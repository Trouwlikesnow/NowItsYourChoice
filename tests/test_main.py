from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scripts.main import cleanup_rolling_window, process_ticker


def _make_df(n=30, base=10.0):
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n),
        "open": [base + i * 0.1 for i in range(n)],
        "close": [base + i * 0.1 for i in range(n)],
        "high": [base + i * 0.1 + 0.5 for i in range(n)],
        "low": [base + i * 0.1 - 0.5 for i in range(n)],
        "volume": [100] * n,
        "amount": [1000] * n,
    })


def _cfg():
    cfg = MagicMock()
    cfg.indicators_by_period = {"日": ["MA5"], "周": ["MA4"], "月": ["MA6"]}
    cfg.tables.indicators = "tbl_ind"
    cfg.tables.price_snapshots = "tbl_snap"
    cfg.tables.tickers = "tbl_tk"
    cfg.tables.sectors = "tbl_sec"
    cfg.tables.sector_news = "tbl_news"
    cfg.snapshot_window_days = 90
    cfg.news_window_days = 60
    return cfg


def test_process_ticker_writes_indicators_for_each_period(mocker):
    mocker.patch("scripts.main.fetch_kline", return_value=_make_df())
    mocker.patch(
        "scripts.main.compute_indicators",
        return_value=[{"x": 1}],
    )
    bitable = MagicMock()
    bitable.list_records.return_value = []
    ticker = {"record_id": "rec1", "fields": {"股票代码": "002594", "股票名称": "比亚迪"}}

    process_ticker(ticker, _cfg(), bitable)

    ind_calls = [c for c in bitable.batch_create.call_args_list if c.args[0] == "tbl_ind"]
    assert len(ind_calls) == 3


def test_process_ticker_writes_snapshot_and_updates_ticker_on_daily_period(mocker):
    mocker.patch("scripts.main.fetch_kline", return_value=_make_df())
    mocker.patch("scripts.main.compute_indicators", return_value=[{"x": 1}])
    bitable = MagicMock()
    bitable.list_records.return_value = []
    ticker = {"record_id": "rec1", "fields": {"股票代码": "002594", "股票名称": "比亚迪"}}

    process_ticker(ticker, _cfg(), bitable)

    snap_calls = [c for c in bitable.batch_create.call_args_list if c.args[0] == "tbl_snap"]
    assert len(snap_calls) == 1
    bitable.update_record.assert_called_once()
    args, kwargs = bitable.update_record.call_args
    assert args[0] == "tbl_tk"
    assert args[1] == "rec1"
    fields = args[2]
    for k in ["最新收盘价", "当日涨跌幅", "60日最高", "60日最低", "距高点回撤%", "最后更新时间"]:
        assert k in fields


def test_process_ticker_skips_period_if_dataframe_empty(mocker):
    mocker.patch("scripts.main.fetch_kline", return_value=pd.DataFrame())
    bitable = MagicMock()
    ticker = {"record_id": "rec1", "fields": {"股票代码": "002594"}}

    process_ticker(ticker, _cfg(), bitable)

    bitable.batch_create.assert_not_called()
    bitable.batch_delete.assert_not_called()
    bitable.update_record.assert_not_called()


def test_process_ticker_deletes_old_indicators_before_writing_new(mocker):
    mocker.patch("scripts.main.fetch_kline", return_value=_make_df())
    mocker.patch("scripts.main.compute_indicators", return_value=[{"x": 1}])
    bitable = MagicMock()

    def list_side_effect(table_id, filter_=None):
        if filter_ and '"日"' in filter_:
            return [{"record_id": "old_r1"}, {"record_id": "old_r2"}]
        return []

    bitable.list_records.side_effect = list_side_effect
    ticker = {"record_id": "rec1", "fields": {"股票代码": "002594"}}

    process_ticker(ticker, _cfg(), bitable)

    bitable.batch_delete.assert_called_once_with("tbl_ind", ["old_r1", "old_r2"])


def test_cleanup_rolling_window_deletes_only_expired_snapshots():
    cfg = _cfg()
    bitable = MagicMock()

    def list_side_effect(table_id):
        if table_id == "tbl_snap":
            return [
                {"record_id": "r_old", "fields": {"交易日": "2025-01-01"}},
                {"record_id": "r_new", "fields": {"交易日": "2026-05-01"}},
            ]
        return []

    bitable.list_records.side_effect = list_side_effect

    cleanup_rolling_window(cfg, bitable, today="2026-05-08")

    bitable.batch_delete.assert_called_once_with("tbl_snap", ["r_old"])


def test_cleanup_rolling_window_handles_missing_dates_gracefully():
    cfg = _cfg()
    bitable = MagicMock()

    def list_side_effect(table_id):
        if table_id == "tbl_news":
            return [{"record_id": "r1", "fields": {"标题": "no date"}}]
        return []

    bitable.list_records.side_effect = list_side_effect

    cleanup_rolling_window(cfg, bitable, today="2026-05-08")

    bitable.batch_delete.assert_not_called()


def test_main_continues_when_one_ticker_fails(mocker):
    mocker.patch("scripts.main.load_config", return_value=_cfg())
    bitable = MagicMock()

    def list_side_effect(table_id, **kwargs):
        if table_id == "tbl_tk":
            return [
                {"record_id": "r1", "fields": {"股票代码": "001"}},
                {"record_id": "r2", "fields": {"股票代码": "002"}},
            ]
        if table_id == "tbl_sec":
            return []
        return []

    bitable.list_records.side_effect = list_side_effect
    mocker.patch("scripts.main.BitableClient", return_value=bitable)

    pt = mocker.patch(
        "scripts.main.process_ticker",
        side_effect=[RuntimeError("boom"), None],
    )
    mocker.patch("scripts.main.fetch_sector_news", return_value=[])
    mocker.patch("scripts.main.cleanup_rolling_window")

    from scripts.main import main
    main()

    assert pt.call_count == 2
