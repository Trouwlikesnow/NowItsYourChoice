import pandas as pd
import pytest

from scripts.data_fetcher import fetch_kline, fetch_sector_news, resolve_code


def test_fetch_kline_daily_returns_renamed_dataframe(mocker):
    fake_df = pd.DataFrame(
        {
            "日期": ["2026-05-06", "2026-05-07"],
            "开盘": [100.0, 101.0],
            "收盘": [101.0, 102.0],
            "最高": [102.0, 103.0],
            "最低": [99.5, 100.5],
            "成交量": [1000, 1100],
            "成交额": [101000, 112200],
        }
    )
    mocker.patch(
        "scripts.data_fetcher.ak.stock_zh_a_hist", return_value=fake_df
    )
    out = fetch_kline("002594", period="日", days=2)
    assert len(out) == 2
    assert "close" in out.columns
    assert "date" in out.columns
    assert "日期" not in out.columns
    assert out.iloc[-1]["close"] == 102.0
    assert out.iloc[-1]["date"] == pd.Timestamp("2026-05-07")


def test_fetch_kline_returns_empty_dataframe_when_akshare_returns_none(mocker):
    mocker.patch("scripts.data_fetcher.ak.stock_zh_a_hist", return_value=None)
    out = fetch_kline("002594")
    assert isinstance(out, pd.DataFrame)
    assert out.empty


def test_fetch_kline_returns_empty_dataframe_when_akshare_returns_empty(mocker):
    mocker.patch(
        "scripts.data_fetcher.ak.stock_zh_a_hist", return_value=pd.DataFrame()
    )
    out = fetch_kline("002594")
    assert isinstance(out, pd.DataFrame)
    assert out.empty


def test_fetch_kline_uses_correct_period_mapping(mocker):
    fake_df = pd.DataFrame(
        {
            "日期": ["2026-05-07"],
            "开盘": [100.0],
            "收盘": [101.0],
            "最高": [102.0],
            "最低": [99.0],
            "成交量": [1000],
            "成交额": [101000],
        }
    )
    mock_hist = mocker.patch(
        "scripts.data_fetcher.ak.stock_zh_a_hist", return_value=fake_df
    )
    fetch_kline("002594", period="周")
    mock_hist.assert_called_once()
    kwargs = mock_hist.call_args.kwargs
    assert kwargs["period"] == "weekly"
    assert kwargs["adjust"] == "qfq"


def test_resolve_code_returns_six_digit_code_unchanged():
    assert resolve_code("002594") == "002594"


def test_resolve_code_looks_up_by_name(mocker):
    mocker.patch(
        "scripts.data_fetcher.ak.stock_info_a_code_name",
        return_value=pd.DataFrame(
            {"code": ["002594", "300750"], "name": ["比亚迪", "宁德时代"]}
        ),
    )
    assert resolve_code("比亚迪") == "002594"
    assert resolve_code("宁德时代") == "300750"
    assert resolve_code("不存在") is None


def test_fetch_sector_news_normalizes_fields(mocker):
    fake_df = pd.DataFrame(
        {
            "标题": ["利好消息", "下跌警告"],
            "摘要": ["...", "..."],
            "来源": ["东方财富", "新浪"],
            "链接": ["https://example.com/1", "https://example.com/2"],
            "发布时间": ["2026-05-07 10:30:00", "2026-05-07 09:00:00"],
        }
    )
    mocker.patch(
        "scripts.data_fetcher.ak.stock_news_em", return_value=fake_df
    )
    items = fetch_sector_news("BK0123")
    assert len(items) == 2
    assert items[0]["title"] == "利好消息"
    assert items[0]["url"] == "https://example.com/1"
    assert items[0]["source"] == "东方财富"
    assert "标题" not in items[0]


def test_fetch_sector_news_respects_limit(mocker):
    fake_df = pd.DataFrame(
        {
            "标题": [f"标题{i}" for i in range(30)],
            "摘要": ["摘要" for _ in range(30)],
            "来源": ["来源" for _ in range(30)],
            "链接": [f"https://example.com/{i}" for i in range(30)],
            "发布时间": ["2026-05-07 10:30:00" for _ in range(30)],
        }
    )
    mocker.patch(
        "scripts.data_fetcher.ak.stock_news_em", return_value=fake_df
    )
    items = fetch_sector_news("BK0123", limit=5)
    assert len(items) == 5


def test_fetch_sector_news_returns_empty_list_when_no_data(mocker):
    mocker.patch("scripts.data_fetcher.ak.stock_news_em", return_value=None)
    assert fetch_sector_news("BK0123") == []
