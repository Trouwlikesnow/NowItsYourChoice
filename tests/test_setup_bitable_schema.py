from scripts.setup_bitable_schema import (
    schema_for_sectors,
    schema_for_tickers,
    schema_for_indicators,
    schema_for_price_snapshots,
    schema_for_sector_news,
    schema_for_decisions,
    schema_for_trading_rules,
    schema_for_trades,
    schema_for_portfolio,
    schema_for_asset_snapshots,
    FT_TEXT, FT_NUMBER, FT_SINGLE_SELECT, FT_DATE_TIME, FT_URL, FT_DUPLEX_LINK,
)


VALID_TYPES = {FT_TEXT, FT_NUMBER, FT_SINGLE_SELECT, FT_DATE_TIME, FT_URL, FT_DUPLEX_LINK}


def _assert_well_formed(schema, with_link_to=None):
    assert len(schema) >= 1
    seen_names = set()
    for f in schema:
        assert f.name and isinstance(f.name, str)
        assert f.name not in seen_names, f"duplicate field name {f.name}"
        seen_names.add(f.name)
        assert f.type in VALID_TYPES, f"invalid type {f.type} for {f.name}"
        if f.type == FT_SINGLE_SELECT:
            assert "options" in f.property
            assert all("name" in opt for opt in f.property["options"])
        if f.type == FT_DUPLEX_LINK:
            assert "table_id" in f.property
            if with_link_to:
                assert f.property["table_id"] == with_link_to


def test_sectors_schema_well_formed():
    _assert_well_formed(schema_for_sectors())


def test_tickers_schema_well_formed_and_links_to_sectors():
    _assert_well_formed(schema_for_tickers("tbl_sectors_dummy"), with_link_to="tbl_sectors_dummy")


def test_indicators_schema_includes_all_indicator_options():
    schema = schema_for_indicators()
    indicator_field = next(f for f in schema if f.name == "指标名")
    names = {opt["name"] for opt in indicator_field.property["options"]}
    # spot-check coverage; at minimum all the Phase 1 indicators
    assert {"MA5", "MA20", "MA60", "MACD-DIF", "RSI14", "KDJ-K", "BOLL-UPPER"}.issubset(names)


def test_sector_news_schema_links_to_sectors():
    _assert_well_formed(schema_for_sector_news("tbl_xx"), with_link_to="tbl_xx")


def test_decisions_schema_well_formed():
    _assert_well_formed(schema_for_decisions())


def test_trading_rules_schema_well_formed():
    _assert_well_formed(schema_for_trading_rules())


def test_price_snapshots_schema_well_formed():
    _assert_well_formed(schema_for_price_snapshots())


def test_trades_schema_well_formed():
    schema = schema_for_trades()
    _assert_well_formed(schema)
    names = {f.name for f in schema}
    assert {"交易时间", "股票代码", "股票名称", "方向", "成交价", "成交数量",
            "成交金额", "佣金", "印花税", "过户费", "手续费合计", "券商",
            "来源", "识别状态"}.issubset(names)
    direction_field = next(f for f in schema if f.name == "方向")
    option_names = {o["name"] for o in direction_field.property["options"]}
    assert option_names == {"买入", "卖出"}


def test_portfolio_schema_well_formed_and_links_to_sectors():
    schema = schema_for_portfolio("tbl_sec_dummy")
    _assert_well_formed(schema, with_link_to="tbl_sec_dummy")
    names = {f.name for f in schema}
    assert {"股票代码", "股票名称", "券商", "资金属性", "所属板块", "持仓数量",
            "成本价", "成本金额", "当前价", "市值", "浮盈额", "浮盈%",
            "仓位占比%", "仓位预警"}.issubset(names)


def test_asset_snapshots_schema_well_formed():
    schema = schema_for_asset_snapshots()
    _assert_well_formed(schema)
    names = {f.name for f in schema}
    assert {"日期", "券商", "资金属性", "总市值", "总成本", "总浮盈",
            "总浮盈%", "当日盈亏", "持仓只数"}.issubset(names)
