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
        elif name == "RSI14":
            rows.extend(_compute_rsi(code, df, period, update_time))
        elif name == "KDJ":
            rows.extend(_compute_kdj(code, df, period, update_time))
        elif name == "BOLL":
            rows.extend(_compute_boll(code, df, period, update_time))
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


def _compute_rsi(code, df, period, update_time):
    series = ta.rsi(df["close"], length=14)
    if series is None:
        return []
    cur, prev = _last_two(series)
    if cur is None:
        return []
    if cur > 80:
        state = "超买"
    elif cur < 20:
        state = "超卖"
    elif cur >= 50:
        state = "偏强"
    else:
        state = "偏弱"
    return [_row(code, period, "RSI14", round(cur, 2),
                 round(prev, 2) if prev is not None else None, state, update_time)]


def _kdj_state(cur):
    if cur > 80:
        return "高位"
    if cur < 20:
        return "低位"
    return "中位"


def _compute_kdj(code, df, period, update_time):
    res = ta.kdj(df["high"], df["low"], df["close"])
    if res is None or res.empty:
        return []
    k_col = next((c for c in res.columns if c.startswith("K_")), None)
    d_col = next((c for c in res.columns if c.startswith("D_")), None)
    j_col = next((c for c in res.columns if c.startswith("J_")), None)
    rows = []
    for label, col in (("KDJ-K", k_col), ("KDJ-D", d_col), ("KDJ-J", j_col)):
        if col is None:
            continue
        cur, prev = _last_two(res[col])
        if cur is None:
            continue
        rows.append(_row(code, period, label, round(cur, 2),
                         round(prev, 2) if prev is not None else None,
                         _kdj_state(cur), update_time))
    return rows


def _compute_boll(code, df, period, update_time):
    res = ta.bbands(df["close"], length=20, std=2)
    if res is None or res.empty:
        return []
    lower_col = next((c for c in res.columns if c.startswith("BBL_")), None)
    mid_col = next((c for c in res.columns if c.startswith("BBM_")), None)
    upper_col = next((c for c in res.columns if c.startswith("BBU_")), None)
    rows = []
    for label, col in (("BOLL-UPPER", upper_col), ("BOLL-MID", mid_col), ("BOLL-LOWER", lower_col)):
        if col is None:
            continue
        cur, prev = _last_two(res[col])
        if cur is None:
            continue
        rows.append(_row(code, period, label, round(cur, 4),
                         round(prev, 4) if prev is not None else None, "", update_time))
    return rows
