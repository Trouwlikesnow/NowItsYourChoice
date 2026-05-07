import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass
class TableIds:
    sectors: str
    tickers: str
    indicators: str
    price_snapshots: str
    sector_news: str
    decisions: str
    trading_rules: str


@dataclass
class Config:
    feishu_app_id: str
    feishu_app_secret: str
    feishu_base_app_token: str
    tables: TableIds
    indicators_by_period: dict[str, list[str]] = field(
        default_factory=lambda: {
            "日": ["MA5", "MA10", "MA20", "MA60", "MACD", "RSI14", "KDJ", "BOLL"],
            "周": ["MA4", "MA13", "MA26", "MACD", "RSI14"],
            "月": ["MA6", "MA12", "MACD"],
        }
    )
    snapshot_window_days: int = 90
    news_window_days: int = 60


def load_config() -> Config:
    load_dotenv()
    tables = TableIds(
        sectors=os.environ["TABLE_ID_SECTORS"],
        tickers=os.environ["TABLE_ID_TICKERS"],
        indicators=os.environ["TABLE_ID_INDICATORS"],
        price_snapshots=os.environ["TABLE_ID_PRICE_SNAPSHOTS"],
        sector_news=os.environ["TABLE_ID_SECTOR_NEWS"],
        decisions=os.environ["TABLE_ID_DECISIONS"],
        trading_rules=os.environ["TABLE_ID_TRADING_RULES"],
    )
    return Config(
        feishu_app_id=os.environ["FEISHU_APP_ID"],
        feishu_app_secret=os.environ["FEISHU_APP_SECRET"],
        feishu_base_app_token=os.environ["FEISHU_BASE_APP_TOKEN"],
        tables=tables,
    )
