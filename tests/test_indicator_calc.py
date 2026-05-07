import pandas as pd
import pytest

from scripts.indicator_calc import compute_indicators


def _make_df(closes):
    n = len(closes)
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n),
        "open": closes,
        "close": closes,
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "volume": [1] * n,
        "amount": [1] * n,
    })


def test_returns_empty_for_empty_or_none_dataframe():
    assert compute_indicators("002594", None, "日", ["MA20"]) == []
    assert compute_indicators("002594", pd.DataFrame(), "日", ["MA20"]) == []


def test_includes_ma_with_correct_value_and_state():
    df = _make_df([float(i) for i in range(1, 31)])
    rows = compute_indicators("002594", df, "日", ["MA5", "MA20"])
    assert len(rows) == 2
    ma20 = next(r for r in rows if r["指标名"] == "MA20")
    assert ma20["当前值"] == pytest.approx(20.5)
    assert ma20["信号状态"] == "上行"
    assert ma20["更新时间"] == "2025-01-30"
    assert ma20["复合主键"] == "002594_日_MA20"
    assert ma20["股票代码"] == "002594"
    assert ma20["周期"] == "日"


def test_macd_emits_three_subindicators():
    df = _make_df([10.0 + 0.1 * i for i in range(60)])
    rows = compute_indicators("002594", df, "日", ["MACD"])
    names = {r["指标名"] for r in rows}
    assert names == {"MACD-DIF", "MACD-DEA", "MACD-HIST"}
    for r in rows:
        assert isinstance(r["当前值"], float)
        assert r["更新时间"]
