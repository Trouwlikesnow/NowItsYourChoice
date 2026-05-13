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
