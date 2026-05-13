import pytest


ALL_ENV_VARS = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_BASE_APP_TOKEN",
    "TABLE_ID_SECTORS",
    "TABLE_ID_TICKERS",
    "TABLE_ID_INDICATORS",
    "TABLE_ID_PRICE_SNAPSHOTS",
    "TABLE_ID_SECTOR_NEWS",
    "TABLE_ID_DECISIONS",
    "TABLE_ID_TRADING_RULES",
    "TABLE_ID_TRADES",
    "TABLE_ID_PORTFOLIO",
    "TABLE_ID_ASSET_SNAPSHOTS",
]


def _clear_all_env(monkeypatch):
    for name in ALL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _set_all_env(monkeypatch):
    _clear_all_env(monkeypatch)
    monkeypatch.setenv("FEISHU_APP_ID", "id1")
    monkeypatch.setenv("FEISHU_APP_SECRET", "s1")
    monkeypatch.setenv("FEISHU_BASE_APP_TOKEN", "bt1")
    monkeypatch.setenv("TABLE_ID_SECTORS", "t_sec")
    monkeypatch.setenv("TABLE_ID_TICKERS", "t_tck")
    monkeypatch.setenv("TABLE_ID_INDICATORS", "t_ind")
    monkeypatch.setenv("TABLE_ID_PRICE_SNAPSHOTS", "t_snap")
    monkeypatch.setenv("TABLE_ID_SECTOR_NEWS", "t_news")
    monkeypatch.setenv("TABLE_ID_DECISIONS", "t_dec")
    monkeypatch.setenv("TABLE_ID_TRADING_RULES", "t_rul")
    monkeypatch.setenv("TABLE_ID_TRADES", "t_trd")
    monkeypatch.setenv("TABLE_ID_PORTFOLIO", "t_pf")
    monkeypatch.setenv("TABLE_ID_ASSET_SNAPSHOTS", "t_as")


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setattr("scripts.config.load_dotenv", lambda: None)
    _set_all_env(monkeypatch)
    from scripts.config import load_config

    cfg = load_config()
    assert cfg.feishu_app_id == "id1"
    assert cfg.feishu_app_secret == "s1"
    assert cfg.feishu_base_app_token == "bt1"
    assert cfg.tables.sectors == "t_sec"
    assert cfg.tables.tickers == "t_tck"
    assert cfg.tables.indicators == "t_ind"
    assert cfg.tables.price_snapshots == "t_snap"
    assert cfg.tables.sector_news == "t_news"
    assert cfg.tables.decisions == "t_dec"
    assert cfg.tables.trading_rules == "t_rul"
    assert cfg.tables.trades == "t_trd"
    assert cfg.tables.portfolio == "t_pf"
    assert cfg.tables.asset_snapshots == "t_as"


def test_load_config_default_indicator_periods(monkeypatch):
    monkeypatch.setattr("scripts.config.load_dotenv", lambda: None)
    _set_all_env(monkeypatch)
    from scripts.config import load_config

    cfg = load_config()
    assert "MA20" in cfg.indicators_by_period["日"]
    assert "MACD" in cfg.indicators_by_period["周"]
    assert "MA12" in cfg.indicators_by_period["月"]
    assert cfg.snapshot_window_days == 90
    assert cfg.news_window_days == 60


def test_load_config_raises_on_missing_required_env(monkeypatch):
    monkeypatch.setattr("scripts.config.load_dotenv", lambda: None)
    _set_all_env(monkeypatch)
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    from scripts.config import load_config

    with pytest.raises(KeyError):
        load_config()
