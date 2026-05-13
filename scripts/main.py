import logging
import traceback
from datetime import datetime, timedelta

import pandas as pd

from scripts.bitable_client import BitableClient
from scripts.config import load_config
from scripts.data_fetcher import fetch_kline, fetch_sector_news
from scripts.indicator_calc import compute_indicators
from scripts.portfolio import (
    sync_portfolio,
    refresh_market_values,
    check_position_alerts,
    take_asset_snapshot,
    cleanup_asset_snapshots,
)

log = logging.getLogger(__name__)


def _to_ms(value):
    # Feishu date/datetime fields require millisecond Unix timestamps, not strings.
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(pd.Timestamp(value).timestamp() * 1000)
    except (ValueError, TypeError):
        return None


def process_ticker(ticker, cfg, bitable):
    fields = ticker.get("fields", {})
    code = fields.get("股票代码")
    daily_df = None

    for period, indicator_list in cfg.indicators_by_period.items():
        df = fetch_kline(code, period=period, days=250)
        if df is None or df.empty:
            continue

        rows = compute_indicators(code, df, period, indicator_list)
        if rows:
            for r in rows:
                if "更新时间" in r:
                    r["更新时间"] = _to_ms(r["更新时间"])
            old = bitable.list_records(
                cfg.tables.indicators,
                filter_=f'AND(CurrentValue.[股票代码] = "{code}", CurrentValue.[周期] = "{period}")',
            )
            old_ids = [r["record_id"] for r in old]
            if old_ids:
                bitable.batch_delete(cfg.tables.indicators, old_ids)
            bitable.batch_create(cfg.tables.indicators, rows)

        if period == "日":
            daily_df = df

    if daily_df is not None and not daily_df.empty:
        last = daily_df.iloc[-1]
        last_close = float(last["close"])
        date_str = last["date"].strftime("%Y%m%d")
        snapshot_row = {
            "复合主键": f"{code}_{date_str}",
            "股票代码": code,
            "交易日": _to_ms(last["date"]),
            "开盘价": float(last["open"]),
            "收盘价": last_close,
            "最高价": float(last["high"]),
            "最低价": float(last["low"]),
            "成交量": float(last["volume"]),
            "成交额": float(last["amount"]),
        }
        bitable.batch_create(cfg.tables.price_snapshots, [snapshot_row])

        change_pct = (
            round((last_close / float(daily_df.iloc[-2]["close"]) - 1) * 100, 2)
            if len(daily_df) >= 2
            else 0.0
        )
        high60 = float(daily_df.tail(60)["high"].max())
        low60 = float(daily_df.tail(60)["low"].min())
        update_fields = {
            "最新收盘价": last_close,
            "当日涨跌幅": change_pct,
            "当日成交量": float(last["volume"]),
            "60日最高": high60,
            "60日最低": low60,
            "距高点回撤%": round((last_close / high60 - 1) * 100, 2),
            "最后更新时间": _to_ms(last["date"]),
        }
        bitable.update_record(cfg.tables.tickers, ticker["record_id"], update_fields)


def cleanup_rolling_window(cfg, bitable, today=None):
    today_dt = datetime.fromisoformat(today) if today else datetime.now()
    snap_cutoff_ms = _to_ms(today_dt - timedelta(days=cfg.snapshot_window_days))
    news_cutoff_ms = _to_ms(today_dt - timedelta(days=cfg.news_window_days))

    snaps = bitable.list_records(cfg.tables.price_snapshots)
    expired_snaps = []
    for r in snaps:
        ms = _to_ms(r.get("fields", {}).get("交易日"))
        if ms is not None and ms < snap_cutoff_ms:
            expired_snaps.append(r["record_id"])
    if expired_snaps:
        bitable.batch_delete(cfg.tables.price_snapshots, expired_snaps)

    news = bitable.list_records(cfg.tables.sector_news)
    expired_news = []
    for r in news:
        ms = _to_ms(r.get("fields", {}).get("发布时间"))
        if ms is not None and ms < news_cutoff_ms:
            expired_news.append(r["record_id"])
    if expired_news:
        bitable.batch_delete(cfg.tables.sector_news, expired_news)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    bitable = BitableClient(cfg.feishu_app_id, cfg.feishu_app_secret, cfg.feishu_base_app_token)

    failed = []
    tickers = bitable.list_records(cfg.tables.tickers)
    for t in tickers:
        code = t.get("fields", {}).get("股票代码", "?")
        try:
            process_ticker(t, cfg, bitable)
        except Exception as e:
            log.error("ticker %s failed: %s\n%s", code, e, traceback.format_exc())
            failed.append((code, str(e)))

    sectors = bitable.list_records(cfg.tables.sectors)
    for s in sectors:
        sf = s.get("fields", {})
        sector_code = sf.get("板块代码")
        sector_name = sf.get("板块名称") or sf.get("板块名")
        if not sector_code:
            continue
        try:
            news = fetch_sector_news(sector_code)
            if news:
                rows = [
                    {
                        "板块名": [sector_name],
                        "标题": n.get("title"),
                        "摘要": n.get("summary"),
                        "来源": n.get("source"),
                        "URL": n.get("url"),
                        "发布时间": _to_ms(n.get("published_at")),
                    }
                    for n in news
                ]
                bitable.batch_create(cfg.tables.sector_news, rows)
        except Exception as e:
            log.error("sector %s news failed: %s", sector_code, e)

    cleanup_rolling_window(cfg, bitable)

    # --- Phase 2: Portfolio management ---
    sync_portfolio(cfg, bitable)
    refresh_market_values(cfg, bitable)
    check_position_alerts(cfg, bitable)
    take_asset_snapshot(cfg, bitable)
    cleanup_asset_snapshots(cfg, bitable)

    if failed:
        log.warning("failed tickers: %s", failed)


if __name__ == "__main__":
    main()
