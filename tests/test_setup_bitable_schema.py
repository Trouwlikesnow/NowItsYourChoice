from scripts.setup_bitable_schema import (
    schema_for_sectors,
    schema_for_tickers,
    schema_for_indicators,
    schema_for_price_snapshots,
    schema_for_sector_news,
    schema_for_decisions,
    schema_for_trading_rules,
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
