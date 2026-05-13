import pytest

from scripts.portfolio import estimate_fees, apply_trade_to_position


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
