"""Configurable technical-indicator calculator.

Takes K-line OHLCV data + a list of indicator names and emits long-format
dicts (one per (ticker, period, indicator)) for the Bitable indicator table.
"""
from __future__ import annotations

import math
import re
from typing import Optional

import pandas as pd
import pandas_ta as ta


_MA_RE = re.compile(r"^MA(\d+)$")


def compute_indicators(
    code: str,
    df: pd.DataFrame,
    period: str,
    indicators: list[str],
) -> list[dict]:
    if df is None or len(df) == 0:
        return []

    last_date = df["date"].iloc[-1]
    update_time = str(last_date.date()) if hasattr(last_date, "date") else str(last_date)

    rows: list[dict] = []
    for name in indicators:
        ma_match = _MA_RE.match(name)
        if ma_match:
            window = int(ma_match.group(1))
            rows.extend(_compute_ma(code, df, period, name, window, update_time))
        elif name == "MACD":
            rows.extend(_compute_macd(code, df, period, update_time))
        # unknown -> silently skip
    return rows


def _row(code, period, name, cur, prev, state, update_time):
    return {
        "复合主键": f"{code}_{period}_{name}",
        "股票代码": code,
        "周期": period,
        "指标名": name,
        "当前值": cur,
        "前值": prev,
        "信号状态": state,
        "更新时间": update_time,
    }


def _last_two(series):
    if series is None or len(series) == 0:
        return None, None
    cur = series.iloc[-1]
    prev = series.iloc[-2] if len(series) >= 2 else None
    if cur is None or (isinstance(cur, float) and math.isnan(cur)):
        return None, None
    if prev is not None and isinstance(prev, float) and math.isnan(prev):
        prev = None
    return float(cur), (float(prev) if prev is not None else None)


def _ma_state(cur, prev):
    if prev is None or cur == prev:
        return "横盘"
    return "上行" if cur > prev else "下行"


def _compute_ma(code, df, period, name, window, update_time):
    series = df["close"].rolling(window).mean()
    cur, prev = _last_two(series)
    if cur is None:
        return []
    return [_row(code, period, name, round(cur, 4),
                 round(prev, 4) if prev is not None else None,
                 _ma_state(cur, prev), update_time)]


def _hist_state(cur, prev):
    if prev is not None and prev <= 0 < cur:
        return "金叉(0日前)"
    if prev is not None and prev >= 0 > cur:
        return "死叉(0日前)"
    return "多头" if cur > 0 else "空头"


def _compute_macd(code, df, period, update_time):
    res = ta.macd(df["close"])
    if res is None or res.empty:
        return []
    macd_col = next((c for c in res.columns if c.startswith("MACD_")), None)
    hist_col = next((c for c in res.columns if c.startswith("MACDh_")), None)
    sig_col = next((c for c in res.columns if c.startswith("MACDs_")), None)
    rows = []
    for label, col in (("MACD-DIF", macd_col), ("MACD-DEA", sig_col), ("MACD-HIST", hist_col)):
        if col is None:
            continue
        cur, prev = _last_two(res[col])
        if cur is None:
            continue
        if label == "MACD-HIST":
            state = _hist_state(cur, prev)
        elif prev is None:
            state = "横盘"
        else:
            state = "上行" if cur > prev else "下行"
        rows.append(_row(code, period, label, round(cur, 4),
                         round(prev, 4) if prev is not None else None, state, update_time))
    return rows
