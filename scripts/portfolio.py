"""Portfolio management: fee calculation, position sync, market refresh, snapshots."""

from __future__ import annotations

import logging
from datetime import datetime

log = logging.getLogger(__name__)


# Broker commission rates (per-amount ratios)
BROKER_COMMISSION = {
    "招商": 0.00025,   # 万 2.5
    "华泰": 0.0001,    # 万 1
}
MIN_COMMISSION = 5.0        # 最低佣金 5 元
STAMP_TAX_RATE = 0.0005     # 印花税 0.05%, 仅卖出
TRANSFER_FEE_RATE = 0.00001 # 过户费 0.001%


def estimate_fees(amount: float, direction: str, broker: str) -> dict:
    """Estimate trading fees for a single trade.

    Returns dict with keys: 佣金, 印花税, 过户费, 手续费合计.
    """
    rate = BROKER_COMMISSION.get(broker, BROKER_COMMISSION["招商"])
    commission = round(max(amount * rate, MIN_COMMISSION), 2)
    stamp_tax = round(amount * STAMP_TAX_RATE, 2) if direction == "卖出" else 0.0
    transfer_fee = round(amount * TRANSFER_FEE_RATE, 2)
    return {
        "佣金": commission,
        "印花税": stamp_tax,
        "过户费": transfer_fee,
        "手续费合计": round(commission + stamp_tax + transfer_fee, 2),
    }


def apply_trade_to_position(
    existing: dict | None,
    direction: str,
    quantity: int,
    amount: float,
    total_fee: float,
) -> dict:
    """Apply a single trade to a position, returning updated position fields.

    Uses broker-style diluted cost: fees are added to cost on both buy and sell.
    On sell, cost_amount = old_cost - sell_amount + fee, so profitable sells
    lower the cost basis of remaining shares (matching broker app display).

    Args:
        existing: Current position dict with keys 持仓数量, 成本金额, 成本价.
                  None if this is a new position.
        direction: "买入" or "卖出".
        quantity: Number of shares traded.
        amount: Trade amount in yuan (price × quantity).
        total_fee: Total fees for this trade.

    Returns:
        Dict with updated 持仓数量, 成本金额, 成本价.
    """
    old_qty = existing["持仓数量"] if existing else 0
    old_cost_amount = existing["成本金额"] if existing else 0.0

    if direction == "买入":
        new_qty = old_qty + quantity
        new_cost_amount = old_cost_amount + amount + total_fee
    else:  # 卖出
        new_qty = old_qty - quantity
        new_cost_amount = old_cost_amount - amount + total_fee

    if new_qty <= 0:
        return {"持仓数量": 0, "成本金额": 0, "成本价": 0}

    new_cost_price = round(new_cost_amount / new_qty, 2)
    return {
        "持仓数量": new_qty,
        "成本金额": round(new_cost_amount, 2),
        "成本价": new_cost_price,
    }


def _text(v):
    """Extract plain text from a Bitable field value."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in v
        ).strip()
    return str(v).strip()


def _num(v, default=0.0):
    """Extract a numeric value from a Bitable field."""
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _to_ms(value):
    """Convert a date/datetime value to millisecond Unix timestamp for Feishu."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    try:
        import pandas as pd
        return int(pd.Timestamp(value).timestamp() * 1000)
    except (ValueError, TypeError):
        return None


def sync_portfolio(cfg, bitable) -> None:
    """Read unprocessed confirmed trades and update portfolio positions."""
    trades = bitable.list_records(cfg.tables.trades)
    confirmed = [
        t for t in trades
        if _text(t.get("fields", {}).get("识别状态")) == "已确认"
        and not _text(t.get("fields", {}).get("已同步"))
    ]
    if not confirmed:
        log.info("No new confirmed trades to sync")
        return

    # Group trades by (stock code, broker)
    by_key: dict[tuple[str, str], list[dict]] = {}
    for t in confirmed:
        code = _text(t["fields"].get("股票代码"))
        broker = _text(t["fields"].get("券商")) or "招商"
        if code:
            by_key.setdefault((code, broker), []).append(t)

    for (code, broker), code_trades in by_key.items():
        # Look up existing position by (code + broker)
        positions = bitable.list_records(
            cfg.tables.portfolio,
            filter_=f'AND(CurrentValue.[股票代码] = "{code}", CurrentValue.[券商] = "{broker}")',
        )
        existing = None
        pos_record_id = None
        if positions:
            pos_record_id = positions[0]["record_id"]
            pf = positions[0]["fields"]
            existing = {
                "持仓数量": _num(pf.get("持仓数量")),
                "成本金额": _num(pf.get("成本金额")),
                "成本价": _num(pf.get("成本价")),
            }

        # Apply trades in order
        for t in code_trades:
            f = t["fields"]
            result = apply_trade_to_position(
                existing=existing,
                direction=_text(f.get("方向")),
                quantity=int(_num(f.get("成交数量"))),
                amount=_num(f.get("成交金额")),
                total_fee=_num(f.get("手续费合计")),
            )
            existing = result

        # Write back
        if pos_record_id:
            bitable.update_record(cfg.tables.portfolio, pos_record_id, existing)
        else:
            name = _text(code_trades[0]["fields"].get("股票名称"))
            record = {
                "股票代码": code,
                "股票名称": name,
                "券商": broker,
                "资金属性": "自有",  # default; user can change in Bitable
                **existing,
            }
            bitable.batch_create(cfg.tables.portfolio, [record])

        # Mark trades as synced
        for t in code_trades:
            bitable.update_record(
                cfg.tables.trades, t["record_id"], {"已同步": "是"}
            )


def _build_price_map(cfg, bitable) -> dict[str, float]:
    """Build code→price map from tickers table + akshare for missing codes."""
    import akshare as ak

    price_map: dict[str, float] = {}

    # 1. From tickers table (already fetched by daily job)
    tickers = bitable.list_records(cfg.tables.tickers)
    for t in tickers:
        code = _text(t["fields"].get("股票代码"))
        price = _num(t["fields"].get("最新收盘价"))
        if code and price:
            price_map[code] = price

    # 2. Collect missing codes from portfolio
    positions = bitable.list_records(cfg.tables.portfolio)
    missing = set()
    for p in positions:
        code = _text(p["fields"].get("股票代码"))
        if code and code not in price_map and _num(p["fields"].get("持仓数量")) > 0:
            missing.add(code)

    if not missing:
        return price_map

    # 3. Try ETF spot data
    try:
        etf_df = ak.fund_etf_spot_em()
        for _, row in etf_df.iterrows():
            c = str(row["代码"])
            if c in missing:
                price_map[c] = float(row["最新价"])
                missing.discard(c)
    except Exception as e:
        log.warning("ETF spot fetch failed: %s", e)

    # 4. Remaining: try stock kline
    for code in list(missing):
        try:
            from scripts.data_fetcher import fetch_kline
            df = fetch_kline(code, days=5)
            if not df.empty:
                price_map[code] = float(df.iloc[-1]["close"])
        except Exception as e:
            log.warning("Price fetch failed for %s: %s", code, e)

    return price_map


def refresh_market_values(cfg, bitable) -> None:
    """Update portfolio market values using latest prices."""
    positions = bitable.list_records(cfg.tables.portfolio)
    price_map = _build_price_map(cfg, bitable)

    for p in positions:
        code = _text(p["fields"].get("股票代码"))
        qty = _num(p["fields"].get("持仓数量"))
        cost_amount = _num(p["fields"].get("成本金额"))
        if qty <= 0 or code not in price_map:
            continue

        current_price = price_map[code]
        market_value = round(qty * current_price, 2)
        profit = round(market_value - cost_amount, 2)
        profit_pct = round(profit / cost_amount * 100, 2) if cost_amount else 0.0

        bitable.update_record(cfg.tables.portfolio, p["record_id"], {
            "当前价": current_price,
            "市值": market_value,
            "浮盈额": profit,
            "浮盈%": profit_pct,
        })


def check_position_alerts(cfg, bitable) -> None:
    """Calculate position percentage and flag any exceeding 20%."""
    positions = bitable.list_records(cfg.tables.portfolio)
    active = [p for p in positions if _num(p["fields"].get("持仓数量")) > 0]

    total_value = sum(_num(p["fields"].get("市值")) for p in active)
    if total_value <= 0:
        return

    for p in active:
        mv = _num(p["fields"].get("市值"))
        pct = round(mv / total_value * 100, 2)
        alert = "超标" if pct > 20 else "正常"
        bitable.update_record(cfg.tables.portfolio, p["record_id"], {
            "仓位占比%": pct,
            "仓位预警": alert,
        })


def take_asset_snapshot(cfg, bitable) -> None:
    """Generate daily asset snapshot rows, grouped by (broker × fund_type) + a total row."""
    positions = bitable.list_records(cfg.tables.portfolio)
    active = [p for p in positions if _num(p["fields"].get("持仓数量")) > 0]

    # Get yesterday's snapshots for daily P&L lookup
    all_snaps = bitable.list_records(cfg.tables.asset_snapshots)
    yesterday_map: dict[tuple[str, str], float] = {}
    for s in all_snaps:
        sf = s.get("fields", {})
        key = (_text(sf.get("券商")), _text(sf.get("资金属性")))
        yesterday_map[key] = _num(sf.get("总市值"))

    # Group active positions by (broker, fund_type)
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in active:
        pf = p["fields"]
        broker = _text(pf.get("券商")) or "招商"
        fund_type = _text(pf.get("资金属性")) or "自有"
        groups.setdefault((broker, fund_type), []).append(p)

    today = datetime.now()
    rows = []

    def _make_row(broker_label, fund_label, pos_list):
        mv = sum(_num(p["fields"].get("市值")) for p in pos_list)
        cost = sum(_num(p["fields"].get("成本金额")) for p in pos_list)
        profit = round(mv - cost, 2)
        profit_pct = round(profit / cost * 100, 2) if cost else 0.0
        prev_mv = yesterday_map.get((broker_label, fund_label), 0.0)
        daily_pnl = round(mv - prev_mv, 2) if prev_mv else 0.0
        return {
            "日期": _to_ms(today),
            "券商": broker_label,
            "资金属性": fund_label,
            "总市值": mv,
            "总成本": cost,
            "总浮盈": profit,
            "总浮盈%": profit_pct,
            "当日盈亏": daily_pnl,
            "持仓只数": len(pos_list),
        }

    for (broker, fund_type), pos_list in groups.items():
        rows.append(_make_row(broker, fund_type, pos_list))

    # Total row
    rows.append(_make_row("全部", "全部", active))

    bitable.batch_create(cfg.tables.asset_snapshots, rows)


def cleanup_asset_snapshots(cfg, bitable) -> None:
    """Delete asset snapshots older than snapshot_window_days."""
    from datetime import timedelta
    cutoff_ms = _to_ms(datetime.now() - timedelta(days=cfg.snapshot_window_days))
    if cutoff_ms is None:
        return

    snaps = bitable.list_records(cfg.tables.asset_snapshots)
    expired = []
    for s in snaps:
        ms = _to_ms(s.get("fields", {}).get("日期"))
        if ms is not None and ms < cutoff_ms:
            expired.append(s["record_id"])
    if expired:
        bitable.batch_delete(cfg.tables.asset_snapshots, expired)
