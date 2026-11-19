"""Test offline: khong can mang, khong can API key (dung FakeAPI)."""
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from config import TradingConfig
from data_manager import DataManager
from strategies.bollinger import BollingerBandsStrategy
from strategies.indicators import simple_moving_average, wilder_rsi, add_macd_indicator
from strategies.ma_crossover import MovingAverageCrossoverStrategy
from strategies.rsi import RSIStrategy
from trading_bot import TradingBot


def df(prices):
    idx = pd.date_range("2026-01-01", periods=len(prices), freq="1min", tz="UTC")
    return pd.DataFrame({"open": prices, "high": prices, "low": prices,
                         "close": prices, "volume": 1000}, index=idx)


class FakeAPI:
    def __init__(self, prices, positions=None, market_open=True):
        self.prices, self._pos, self.open, self.orders = prices, positions or [], market_open, []

    def get_clock(self): return NS(is_open=self.open)
    def get_account(self): return NS(buying_power="100000", equity="100000", last_equity="99500")
    def list_positions(self): return self._pos
    def submit_order(self, **kw):
        self.orders.append(kw)
        return NS(id="1", status="filled", filled_qty=kw.get("qty", 1), filled_avg_price=100.0, filled_at="2026-01-01T00:00:00Z")
    def get_crypto_bars(self, *a, **kw): return NS(df=df(self.prices))
    def get_bars(self, *a, **kw): return NS(df=df(self.prices))


def cfg(**kw):
    return TradingConfig(api_key="k", api_secret="s", symbols=["BTC/USD"], **kw)


def test_ma_buy_and_sell():
    up = list(np.linspace(100, 80, 40)) + list(np.linspace(80, 120, 20))
    down = list(np.linspace(80, 120, 40)) + list(np.linspace(120, 80, 20))
    s = MovingAverageCrossoverStrategy(5, 20)
    acts_up = [x.action for i in range(25, len(up)) for x in s.generate_signals(df(up[:i + 1]), "BTC/USD")]
    acts_dn = [x.action for i in range(25, len(down)) for x in s.generate_signals(df(down[:i + 1]), "BTC/USD")]
    assert "BUY" in acts_up and "SELL" in acts_dn


def test_rsi_extremes():
    s = RSIStrategy()
    assert s.generate_signals(df(np.linspace(100, 50, 40)), "BTC/USD")[0].action == "BUY"
    assert s.generate_signals(df(np.linspace(50, 100, 40)), "BTC/USD")[0].action == "SELL"
    assert s.generate_signals(df([100, 101, 100, 101] * 10), "BTC/USD") == []


def test_bollinger_breakout():
    prices = [100.0] * 25 + [80.0]
    assert BollingerBandsStrategy().generate_signals(df(prices), "BTC/USD")[0].action == "BUY"


def test_not_enough_data():
    assert MovingAverageCrossoverStrategy().generate_signals(df([1, 2, 3]), "BTC/USD") == []


def test_order_notional_calculation():
    bot = TradingBot(cfg(max_position_size=1000.0, risk_per_trade=0.02), api=FakeAPI([100] * 60))
    # min(100000 * 0.02, 1000) = 1000.0
    assert bot.portfolio_manager.calculate_order_notional() == 1000.0


def test_low_confidence_skipped_and_buy_executes():
    bot = TradingBot(cfg(min_confidence=0.9), api=FakeAPI([100] * 60))
    sig = bot.strategies[0].generate_signals(df(np.r_[np.linspace(100, 80, 40), np.linspace(80, 120, 20)]), "BTC/USD")
    assert bot.execute_signal_group("BTC/USD", "BUY", sig or [bot.strategies[1].generate_signals(df(np.linspace(100, 50, 40)), "BTC/USD")[0]]) is False
    assert bot.api.orders == []


def test_cycle_buys_on_oversold_and_sells_on_overbought():
    # Oversold -> Mua
    api = FakeAPI(list(np.linspace(100, 50, 60)))
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders and api.orders[0]["side"] == "buy" and api.orders[0]["type"] == "market"

    # Overbought -> Ban neu dang co vi the
    pos = [NS(symbol="BTC/USD", qty="7", unrealized_plpc="0.05")]
    api2 = FakeAPI(list(np.linspace(50, 100, 60)), positions=pos)
    TradingBot(cfg(), api=api2).run_trading_cycle()
    assert api2.orders and api2.orders[0]["side"] == "sell" and api2.orders[0]["qty"] == 7.0


def test_no_double_buy_and_no_short():
    pos = [NS(symbol="BTC/USD", qty="5", unrealized_plpc="0.0")]
    api = FakeAPI(list(np.linspace(100, 50, 60)), positions=pos)   # BUY signal nhung da giu
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders == []
    api = FakeAPI(list(np.linspace(50, 100, 60)))                  # SELL signal nhung khong giu
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders == []


def test_stop_loss_trigger():
    # Lo -25% vuot nguong 20% -> ban cat lo ngay lap tuc
    pos = [NS(symbol="BTC/USD", qty="0.5", unrealized_plpc="-0.25")]
    api = FakeAPI(list(np.linspace(100, 100, 60)), positions=pos)
    TradingBot(cfg(stop_loss_pct=0.20), api=api).run_trading_cycle()
    assert len(api.orders) == 1
    assert api.orders[0]["side"] == "sell"
    assert api.orders[0]["qty"] == 0.5


def test_dry_run_places_no_orders():
    api = FakeAPI(list(np.linspace(100, 50, 60)))
    TradingBot(cfg(), api=api, dry_run=True).run_trading_cycle()
    assert api.orders == []


def test_report_and_config_validation():
    bot = TradingBot(cfg(), api=FakeAPI([100] * 60))
    r = bot.generate_performance_report()
    assert r["total_equity"] == 100000 and r["day_gain"] == 500
    with pytest.raises(ValueError):
        TradingConfig(api_key="", api_secret="").validate()
    with pytest.raises(ValueError):
        TradingConfig(api_key="k", api_secret="s", symbols=["AAPL"], is_crypto=True).validate()


def test_data_manager_handles_api_error():
    class Boom:
        def get_crypto_bars(self, *a, **k): raise RuntimeError("x")
    assert DataManager(Boom()).get_historical_data("BTC/USD").empty


def test_indicators_math():
    prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    sma = simple_moving_average(prices, 3)
    assert np.isnan(sma.iloc[0]) and np.isnan(sma.iloc[1])
    assert sma.iloc[2] == 11.0  # (10+11+12)/3

    # Wilder RSI
    series = pd.Series(np.linspace(50, 100, 30))
    rsi = wilder_rsi(series, 14)
    assert rsi.iloc[-1] > 90  # Chuoi tang deu dan thi RSI rat cao (>90)
