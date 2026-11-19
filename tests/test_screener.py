"""test_screener.py: Unit tests toan dien cho Stock Screener module."""
import math
import numpy as np
import pandas as pd
import pytest

from config import TradingConfig
from stock_screener import DataQualityValidator, StockMetrics, StockScreener


def make_candle_df(n_bars=60, base_price=100.0, volume=5000, volatility_daily=0.015):
    """Tao nến giả lập có độ biến động thực tế."""
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="B", tz="UTC")
    np.random.seed(42)
    # Tao chuoi gia co bien dong quanh base_price
    returns = np.random.normal(loc=0.0005, scale=volatility_daily, size=n_bars)
    prices = [base_price]
    for r in returns[1:]:
        prices.append(prices[-1] * (1.0 + r))

    prices = np.array(prices)
    return pd.DataFrame({
        "open": prices * 0.998,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": [volume] * n_bars,
    }, index=dates)


class MockDataManager:
    def __init__(self, dfs_dict=None):
        self.dfs = dfs_dict or {}

    def get_daily_bars(self, symbol, days=60):
        return self.dfs.get(symbol, pd.DataFrame())


# =====================================================================
# 1. TEST DATA QUALITY VALIDATOR
# =====================================================================

def test_data_validator_valid():
    df = make_candle_df(60)
    valid, issues = DataQualityValidator.validate(df, "AAPL", min_bars=30)
    assert valid is True
    assert issues == []


def test_data_validator_empty_and_short():
    valid, issues = DataQualityValidator.validate(pd.DataFrame(), "AAPL", min_bars=30)
    assert valid is False
    assert any("rong" in i for i in issues)

    short_df = make_candle_df(15)
    valid, issues = DataQualityValidator.validate(short_df, "AAPL", min_bars=30)
    assert valid is False
    assert any("khong du nguong" in i for i in issues)


def test_data_validator_missing_column_and_nan():
    df = make_candle_df(60).drop(columns=["volume"])
    valid, issues = DataQualityValidator.validate(df, "AAPL", min_bars=30)
    assert valid is False
    assert any("Thieu cac cot" in i for i in issues)

    df_nan = make_candle_df(60)
    df_nan.loc[df_nan.index[5], "close"] = np.nan
    valid, issues = DataQualityValidator.validate(df_nan, "AAPL", min_bars=30)
    assert valid is False
    assert any("NaN/Null" in i for i in issues)


def test_data_validator_price_anomalies():
    # High < Low
    df_bad = make_candle_df(60)
    df_bad.loc[df_bad.index[0], "high"] = 50.0
    df_bad.loc[df_bad.index[0], "low"] = 150.0
    valid, issues = DataQualityValidator.validate(df_bad, "AAPL", min_bars=30)
    assert valid is False
    assert any("High < Low" in i for i in issues)

    # Gia <= 0 hoac Volume am
    df_neg = make_candle_df(60)
    df_neg.loc[df_neg.index[2], "close"] = -10.0
    df_neg.loc[df_neg.index[3], "volume"] = -500
    valid, issues = DataQualityValidator.validate(df_neg, "AAPL", min_bars=30)
    assert valid is False
    assert any("gia close <= 0" in i for i in issues)
    assert any("Volume am" in i for i in issues)


def test_data_validator_duplicate_timestamps():
    df = make_candle_df(60)
    # Tao 1 timestamp trung lap
    df_dup = pd.concat([df, df.iloc[[0]]]).sort_index()
    valid, issues = DataQualityValidator.validate(df_dup, "AAPL", min_bars=30)
    assert valid is False
    assert any("trung lap timestamp" in i for i in issues)


# =====================================================================
# 2. TEST LIQUIDITY (ADV) & VOLATILITY (ANNUALIZED)
# =====================================================================

def test_calculate_liquidity_adv():
    df = pd.DataFrame({
        "open": [100.0] * 10, "high": [101.0] * 10, "low": [99.0] * 10,
        "close": [100.0] * 10, "volume": [2000] * 10
    })
    adv = StockScreener.calculate_liquidity(df)
    assert adv == 200000.0


def test_calculate_volatility_annualized():
    prices = [100.0, 102.0] * 15
    df = pd.DataFrame({"close": prices})
    daily_std, annual_std = StockScreener.calculate_volatility(df)

    assert daily_std > 0
    # Kiem tra cong thuc annual = daily * sqrt(252) voi do chinh xac float
    assert math.isclose(annual_std, daily_std * math.sqrt(252), abs_tol=1e-3)


# =====================================================================
# 3. TEST CORRELATION & GREEDY PRUNING
# =====================================================================

def test_calculate_correlation_matrix():
    dates = pd.date_range("2026-01-01", periods=30, freq="B", tz="UTC")
    # A dao dong: [100, 102, 98, 101...]
    ret_a = np.array([0.02, -0.01, 0.03, -0.02] * 7 + [0.01, -0.01])
    # B dao dong giong het A (cung chieu)
    ret_b = ret_a * 1.5
    # C dao dong nguoc chieu A (nguoc chieu)
    ret_c = -ret_a

    p_a = 100.0 * np.cumprod(1 + np.insert(ret_a, 0, 0))[:-1]
    p_b = 50.0 * np.cumprod(1 + np.insert(ret_b, 0, 0))[:-1]
    p_c = 200.0 * np.cumprod(1 + np.insert(ret_c, 0, 0))[:-1]

    dfs = {
        "A": pd.DataFrame({"close": p_a}, index=dates),
        "B": pd.DataFrame({"close": p_b}, index=dates),
        "C": pd.DataFrame({"close": p_c}, index=dates),
    }

    corr = StockScreener.calculate_correlation_matrix(dfs)
    assert corr.loc["A", "B"] > 0.99
    assert corr.loc["A", "C"] < -0.99


def test_prune_correlated_assets():
    screener = StockScreener(None, None)

    metrics = {
        "AAPL": StockMetrics("AAPL", adv=1000000.0, volatility_annual=0.25),
        "MSFT": StockMetrics("MSFT", adv=800000.0, volatility_annual=0.24),
        "JPM": StockMetrics("JPM", adv=600000.0, volatility_annual=0.20),
    }

    corr_df = pd.DataFrame({
        "AAPL": [1.0, 0.90, 0.30],
        "MSFT": [0.90, 1.0, 0.35],
        "JPM": [0.30, 0.35, 1.0],
    }, index=["AAPL", "MSFT", "JPM"])

    selected, pruned = screener.prune_correlated_assets(
        qualified_symbols=["AAPL", "MSFT", "JPM"],
        metrics_dict=metrics,
        corr_matrix=corr_df,
        max_corr=0.75,
        target_n=3,
    )

    assert selected == ["AAPL", "JPM"]
    assert pruned == ["MSFT"]
    assert metrics["MSFT"].status == "PRUNED_CORRELATION"


# =====================================================================
# 4. TEST FULL SCREENING PIPELINE
# =====================================================================

def test_full_screening_pipeline():
    cfg = TradingConfig(
        api_key="k", api_secret="s",
        screening_universe=["AAPL", "MSFT", "ILLIQUID", "BAD_DATA"],
        screening_lookback_days=50,
        min_adv=200000.0,
        min_volatility=0.10,
        max_volatility=0.60,
        max_correlation=0.75,
        target_top_n=2,
    )

    # AAPL & MSFT co bien dong hop le (vol ~ 24%/nam)
    df_aapl = make_candle_df(50, base_price=150.0, volume=10000, volatility_daily=0.015)
    df_msft = make_candle_df(50, base_price=300.0, volume=8000, volatility_daily=0.015)
    df_illiquid = make_candle_df(50, base_price=10.0, volume=100, volatility_daily=0.015)  # ADV ~ 1k < 200k
    df_bad = make_candle_df(10)  # Khong du nến -> FAILED_DATA

    mock_dm = MockDataManager({
        "AAPL": df_aapl,
        "MSFT": df_msft,
        "ILLIQUID": df_illiquid,
        "BAD_DATA": df_bad,
    })

    screener = StockScreener(mock_dm, cfg)
    res = screener.run_screening()

    assert "BAD_DATA" not in res.valid_data_symbols
    assert res.metrics["BAD_DATA"].status == "FAILED_DATA"
    assert res.metrics["ILLIQUID"].status == "FAILED_LIQUIDITY"
    assert "AAPL" in res.selected_symbols or "MSFT" in res.selected_symbols
    assert len(res.selected_symbols) <= cfg.target_top_n
    assert len(res.summary_df) == 4
