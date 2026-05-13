import pytest
from unittest.mock import MagicMock, call
from scripts.portfolio import (
    estimate_fees,
    apply_trade_to_position,
    sync_portfolio,
    refresh_market_values,
    check_position_alerts,
    take_asset_snapshot,
    cleanup_asset_snapshots,
)


class TestEstimateFees:
    def test_buy_zhaoShang_normal(self):
        # 买入 10万, 招商万2.5 => 佣金=25, 印花税=0, 过户费=1
        fees = estimate_fees(amount=100_000, direction="买入", broker="招商")
        assert fees["佣金"] == 25.0
        assert fees["印花税"] == 0.0
        assert fees["过户费"] == 1.0
        assert fees["手续费合计"] == 26.0

    def test_buy_zhaoShang_min_commission(self):
        # 买入 1000元, 招商万2.5 => 佣金=0.25 < 5 => 佣金=5
        fees = estimate_fees(amount=1_000, direction="买入", broker="招商")
        assert fees["佣金"] == 5.0

    def test_sell_zhaoShang(self):
        # 卖出 10万, 招商万2.5 => 佣金=25, 印花税=50, 过户费=1
        fees = estimate_fees(amount=100_000, direction="卖出", broker="招商")
        assert fees["佣金"] == 25.0
        assert fees["印花税"] == 50.0
        assert fees["过户费"] == 1.0
        assert fees["手续费合计"] == 76.0

    def test_buy_huatai(self):
        # 买入 10万, 华泰万1 => 佣金=10, 印花税=0, 过户费=1
        fees = estimate_fees(amount=100_000, direction="买入", broker="华泰")
        assert fees["佣金"] == 10.0
        assert fees["印花税"] == 0.0
        assert fees["过户费"] == 1.0
        assert fees["手续费合计"] == 11.0

    def test_sell_huatai_min_commission(self):
        # 卖出 1000元, 华泰万1 => 佣金=0.1 < 5 => 佣金=5, 印花税=0.5, 过户费=0.01
        fees = estimate_fees(amount=1_000, direction="卖出", broker="华泰")
        assert fees["佣金"] == 5.0
        assert fees["印花税"] == 0.5
        assert fees["过户费"] == 0.01
        assert fees["手续费合计"] == 5.51

    def test_unknown_broker_defaults_to_zhaoShang(self):
        fees = estimate_fees(amount=100_000, direction="买入", broker="未知")
        assert fees["佣金"] == 25.0  # same as 招商


class TestApplyTradeToPosition:
    def test_buy_new_position(self):
        pos = apply_trade_to_position(
            existing=None,
            direction="买入", quantity=1000, amount=10_000, total_fee=30,
        )
        assert pos["持仓数量"] == 1000
        assert pos["成本金额"] == 10_030
        assert pos["成本价"] == pytest.approx(10.03)

    def test_buy_add_to_existing(self):
        existing = {"持仓数量": 1000, "成本金额": 10_030, "成本价": 10.03}
        pos = apply_trade_to_position(
            existing=existing,
            direction="买入", quantity=500, amount=6_000, total_fee=20,
        )
        assert pos["持仓数量"] == 1500
        assert pos["成本金额"] == 10_030 + 6_000 + 20  # 16050
        assert pos["成本价"] == pytest.approx(16_050 / 1500)

    def test_sell_partial_profit(self):
        existing = {"持仓数量": 1000, "成本金额": 10_030, "成本价": 10.03}
        pos = apply_trade_to_position(
            existing=existing,
            direction="卖出", quantity=500, amount=6_000, total_fee=25,
        )
        assert pos["持仓数量"] == 500
        assert pos["成本金额"] == 4_055
        assert pos["成本价"] == pytest.approx(8.11)

    def test_sell_partial_loss(self):
        existing = {"持仓数量": 1000, "成本金额": 10_030, "成本价": 10.03}
        pos = apply_trade_to_position(
            existing=existing,
            direction="卖出", quantity=500, amount=4_500, total_fee=25,
        )
        assert pos["持仓数量"] == 500
        assert pos["成本金额"] == 5_555
        assert pos["成本价"] == pytest.approx(11.11)

    def test_sell_all_clears_position(self):
        existing = {"持仓数量": 1000, "成本金额": 10_030, "成本价": 10.03}
        pos = apply_trade_to_position(
            existing=existing,
            direction="卖出", quantity=1000, amount=12_000, total_fee=30,
        )
        assert pos["持仓数量"] == 0
        assert pos["成本金额"] == 0
        assert pos["成本价"] == 0


def _cfg():
    cfg = MagicMock()
    cfg.tables.trades = "tbl_trades"
    cfg.tables.portfolio = "tbl_portfolio"
    cfg.tables.tickers = "tbl_tickers"
    cfg.tables.asset_snapshots = "tbl_as"
    cfg.snapshot_window_days = 90
    return cfg


class TestSyncPortfolio:
    def test_buy_creates_new_position(self):
        bitable = MagicMock()
        bitable.list_records.side_effect = [
            [{"record_id": "tr1", "fields": {
                "股票代码": "002594", "股票名称": "比亚迪", "方向": "买入",
                "成交数量": 1000, "成交价": 10.0, "成交金额": 10000,
                "手续费合计": 30, "识别状态": "已确认", "券商": "招商",
            }}],
            [],
        ]

        sync_portfolio(_cfg(), bitable)

        bitable.batch_create.assert_called_once()
        args = bitable.batch_create.call_args
        assert args[0][0] == "tbl_portfolio"
        record = args[0][1][0]
        assert record["股票代码"] == "002594"
        assert record["券商"] == "招商"
        assert record["资金属性"] == "自有"
        assert record["持仓数量"] == 1000
        assert record["成本金额"] == 10030
        assert record["成本价"] == pytest.approx(10.03)

    def test_sell_updates_existing_position(self):
        bitable = MagicMock()
        bitable.list_records.side_effect = [
            [{"record_id": "tr2", "fields": {
                "股票代码": "002594", "股票名称": "比亚迪", "方向": "卖出",
                "成交数量": 500, "成交价": 12.0, "成交金额": 6000,
                "手续费合计": 25, "识别状态": "已确认", "券商": "招商",
            }}],
            [{"record_id": "pf1", "fields": {
                "股票代码": "002594", "券商": "招商", "持仓数量": 1000,
                "成本金额": 10030, "成本价": 10.03,
            }}],
        ]

        sync_portfolio(_cfg(), bitable)

        bitable.update_record.assert_called()
        update_args = bitable.update_record.call_args_list[0]
        assert update_args[0][0] == "tbl_portfolio"
        assert update_args[0][1] == "pf1"
        fields = update_args[0][2]
        assert fields["持仓数量"] == 500
        assert fields["成本金额"] == 4055
        assert fields["成本价"] == pytest.approx(8.11)

    def test_skips_unconfirmed_trades(self):
        bitable = MagicMock()
        bitable.list_records.return_value = [
            {"record_id": "tr3", "fields": {
                "股票代码": "002594", "方向": "买入",
                "成交数量": 100, "成交金额": 1000,
                "手续费合计": 5, "识别状态": "待确认",
            }},
        ]

        sync_portfolio(_cfg(), bitable)

        bitable.batch_create.assert_not_called()
        bitable.update_record.assert_not_called()


class TestRefreshMarketValues:
    def test_updates_market_values(self):
        bitable = MagicMock()
        bitable.list_records.side_effect = [
            [{"record_id": "pf1", "fields": {
                "股票代码": "002594", "持仓数量": 1000,
                "成本金额": 10030, "成本价": 10.03,
            }}],
            [{"record_id": "tk1", "fields": {
                "股票代码": "002594", "最新收盘价": 12.0,
            }}],
        ]

        refresh_market_values(_cfg(), bitable)

        bitable.update_record.assert_called_once()
        args = bitable.update_record.call_args[0]
        assert args[0] == "tbl_portfolio"
        assert args[1] == "pf1"
        fields = args[2]
        assert fields["当前价"] == 12.0
        assert fields["市值"] == 12000
        assert fields["浮盈额"] == pytest.approx(12000 - 10030)
        assert fields["浮盈%"] == pytest.approx((12000 - 10030) / 10030 * 100, rel=0.01)


class TestCheckPositionAlerts:
    def test_marks_over_20_percent_as_alert(self):
        bitable = MagicMock()
        bitable.list_records.return_value = [
            {"record_id": "pf1", "fields": {"持仓数量": 100, "市值": 80000}},
            {"record_id": "pf2", "fields": {"持仓数量": 50, "市值": 20000}},
        ]

        check_position_alerts(_cfg(), bitable)

        calls = bitable.update_record.call_args_list
        assert len(calls) == 2
        assert calls[0][0][2]["仓位预警"] == "超标"
        assert calls[0][0][2]["仓位占比%"] == 80.0
        assert calls[1][0][2]["仓位预警"] == "正常"
        assert calls[1][0][2]["仓位占比%"] == 20.0

    def test_skips_zero_positions(self):
        bitable = MagicMock()
        bitable.list_records.return_value = [
            {"record_id": "pf1", "fields": {"持仓数量": 0, "市值": 0}},
            {"record_id": "pf2", "fields": {"持仓数量": 100, "市值": 50000}},
        ]

        check_position_alerts(_cfg(), bitable)

        calls = bitable.update_record.call_args_list
        assert len(calls) == 1
        assert calls[0][0][1] == "pf2"


class TestTakeAssetSnapshot:
    def test_creates_snapshot_rows_with_dimensions(self):
        bitable = MagicMock()
        bitable.list_records.side_effect = [
            [
                {"record_id": "pf1", "fields": {
                    "持仓数量": 1000, "市值": 12000, "成本金额": 10030,
                    "券商": "招商", "资金属性": "自有",
                }},
                {"record_id": "pf2", "fields": {
                    "持仓数量": 500, "市值": 8000, "成本金额": 7500,
                    "券商": "华泰", "资金属性": "代管",
                }},
            ],
            [],  # yesterday's snapshots
        ]

        take_asset_snapshot(_cfg(), bitable)

        bitable.batch_create.assert_called_once()
        args = bitable.batch_create.call_args[0]
        assert args[0] == "tbl_as"
        rows = args[1]
        assert len(rows) == 3
        total_row = [r for r in rows if r["券商"] == "全部"][0]
        assert total_row["总市值"] == 20000
        assert total_row["持仓只数"] == 2
