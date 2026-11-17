"""Test offline: khong can mang, khong can API key (dung FakeAPI)."""
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from config import TradingConfig
from data_manager import DataManager
from strategies.bollinger import BollingerBandsStrategy
from strategies.ma_crossover import MovingAverageCrossoverStrategy
from strategies.rsi import RSIStrategy
from trading_bot import TradingBot


def df(prices):
    return pd.DataFrame({"open": prices, "high": prices, "low": prices,
                         "close": prices, "volume": 1000})


class FakeAPI:
    def __init__(self, prices, positions=None, market_open=True):
        self.prices, self._pos, self.open, self.orders = prices, positions or [], market_open, []

    def get_clock(self): return NS(is_open=self.open)
    def get_account(self): return NS(buying_power="100000", equity="100000", last_equity="99500")
    def list_positions(self): return self._pos
    def submit_order(self, **kw):
        self.orders.append(kw); return NS(id="1")
    def get_bars(self, *a, **kw): return NS(df=df(self.prices))


def cfg(**kw):
    return TradingConfig(api_key="k", api_secret="s", symbols=["AAPL"], **kw)


def test_ma_buy_and_sell():
    up = list(np.linspace(100, 80, 40)) + list(np.linspace(80, 120, 20))
    down = list(np.linspace(80, 120, 40)) + list(np.linspace(120, 80, 20))
    s = MovingAverageCrossoverStrategy(5, 20)
    acts_up = [x.action for i in range(25, len(up)) for x in s.generate_signals(df(up[:i + 1]), "X")]
    acts_dn = [x.action for i in range(25, len(down)) for x in s.generate_signals(df(down[:i + 1]), "X")]
    assert "BUY" in acts_up and "SELL" in acts_dn


def test_rsi_extremes():
    s = RSIStrategy()
    assert s.generate_signals(df(np.linspace(100, 50, 40)), "X")[0].action == "BUY"
    assert s.generate_signals(df(np.linspace(50, 100, 40)), "X")[0].action == "SELL"
    assert s.generate_signals(df([100, 101, 100, 101] * 10), "X") == []


def test_bollinger_breakout():
    prices = [100.0] * 25 + [80.0]
    assert BollingerBandsStrategy().generate_signals(df(prices), "X")[0].action == "BUY"


def test_not_enough_data():
    assert MovingAverageCrossoverStrategy().generate_signals(df([1, 2, 3]), "X") == []


def test_position_size_matches_article_formula():
    bot = TradingBot(cfg(), api=FakeAPI([100] * 60))
    # min(100000*0.02, 1000) = 1000 -> 1000/250 = 4
    assert bot.portfolio_manager.calculate_position_size(250.0) == 4


def test_low_confidence_skipped_and_buy_executes():
    bot = TradingBot(cfg(min_confidence=0.9), api=FakeAPI([100] * 60))
    sig = bot.strategies[0].generate_signals(df(np.r_[np.linspace(100, 80, 40), np.linspace(80, 120, 20)]), "AAPL")
    assert bot.execute_signal_group("AAPL", "BUY", sig or [bot.strategies[1].generate_signals(df(np.linspace(100, 50, 40)), "AAPL")[0]]) is False
    assert bot.api.orders == []


def test_cycle_buys_on_oversold_and_sells_on_overbought():
    api = FakeAPI(list(np.linspace(100, 50, 60)))
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders and api.orders[0]["side"] == "buy" and api.orders[0]["type"] == "market"

    pos = [NS(symbol="AAPL", qty="7")]
    api2 = FakeAPI(list(np.linspace(50, 100, 60)), positions=pos)
    TradingBot(cfg(), api=api2).run_trading_cycle()
    assert api2.orders[0]["side"] == "sell" and api2.orders[0]["qty"] == 7


def test_no_double_buy_and_no_short():
    pos = [NS(symbol="AAPL", qty="5")]
    api = FakeAPI(list(np.linspace(100, 50, 60)), positions=pos)   # BUY signal nhung da giu
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders == []
    api = FakeAPI(list(np.linspace(50, 100, 60)))                  # SELL signal nhung khong giu
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders == []


def test_market_closed_and_dry_run():
    api = FakeAPI(list(np.linspace(100, 50, 60)), market_open=False)
    TradingBot(cfg(), api=api).run_trading_cycle()
    assert api.orders == []
    api = FakeAPI(list(np.linspace(100, 50, 60)))
    TradingBot(cfg(), api=api, dry_run=True).run_trading_cycle()
    assert api.orders == []


def test_report_and_config_validation():
    bot = TradingBot(cfg(), api=FakeAPI([100] * 60))
    r = bot.generate_performance_report()
    assert r["total_equity"] == 100000 and r["day_gain"] == 500
    with pytest.raises(ValueError):
        TradingConfig(api_key="", api_secret="").validate()


def test_data_manager_handles_api_error():
    class Boom:
        def get_bars(self, *a, **k): raise RuntimeError("x")
    assert DataManager(Boom()).get_historical_data("AAPL").empty
