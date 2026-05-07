"""Thin AkShare wrapper for K-line data, code resolution, and sector news."""

from __future__ import annotations

from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

PERIOD_MAP = {"日": "daily", "周": "weekly", "月": "monthly"}

_KLINE_RENAME = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
}

_NEWS_RENAME = {
    "标题": "title",
    "摘要": "summary",
    "来源": "source",
    "链接": "url",
    "发布时间": "published_at",
}


def fetch_kline(code: str, period: str = "日", days: int = 250) -> pd.DataFrame:
    """Fetch K-line data for a stock and normalize columns to English."""
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days * 2)
    df = ak.stock_zh_a_hist(
        symbol=code,
        period=PERIOD_MAP[period],
        start_date=start_dt.strftime("%Y%m%d"),
        end_date=end_dt.strftime("%Y%m%d"),
        adjust="qfq",
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns=_KLINE_RENAME)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").tail(days).reset_index(drop=True)
    return df


def resolve_code(query: str) -> str | None:
    """Resolve a 6-digit code or Chinese stock name to a canonical code."""
    if query.isdigit() and len(query) == 6:
        return query
    table = ak.stock_info_a_code_name()
    match = table[table["name"] == query]
    if match.empty:
        return None
    return str(match.iloc[0]["code"])


def fetch_sector_news(sector_code: str, limit: int = 20) -> list[dict]:
    """Fetch latest news items for a sector/board."""
    df = ak.stock_news_em(symbol=sector_code)
    if df is None or df.empty:
        return []
    df = df.rename(columns=_NEWS_RENAME)
    return df.head(limit).to_dict(orient="records")
