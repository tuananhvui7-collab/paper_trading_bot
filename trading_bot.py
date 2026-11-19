import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import alpaca_trade_api as tradeapi
import pandas as pd

from config import PAPER_BASE_URL, TradingConfig
from data_manager import DataManager
from models import TradingSignal
from order_manager import OrderManager
from portfolio_manager import PortfolioManager
from strategies.bollinger import BollingerBandsStrategy
from strategies.indicators import simple_moving_average, wilder_rsi
from strategies.ma_crossover import MovingAverageCrossoverStrategy
from strategies.rsi import RSIStrategy


class TradingBot:
    """Dieu phoi: DataManager + Strategies + PortfolioManager + OrderManager."""

    def __init__(self, config: TradingConfig, api=None, dry_run: bool = False,
                 use_bollinger: bool = False):
        config.validate()
        self.config = config
        self.logger = logging.getLogger("TradingBot")
        # Crypto bot is paper-only and does not use the stock market clock.
        self.api = api or tradeapi.REST(config.api_key, config.api_secret,
                                        base_url=PAPER_BASE_URL, api_version="v2")
        self.data_manager = DataManager(self.api, feed=getattr(config, "data_feed", "iex"))
        self.portfolio_manager = PortfolioManager(self.api, config)
        self.order_manager = OrderManager(self.api, dry_run=dry_run)
        self.strategies = [MovingAverageCrossoverStrategy(), RSIStrategy()]
        if use_bollinger:
            self.strategies.append(BollingerBandsStrategy())

    # ---- chu ky giao dich ----
    def run_trading_cycle(self) -> None:
        if not getattr(self.config, "is_crypto", True):
            try:
                clock = self.api.get_clock()
                if clock and not getattr(clock, "is_open", True):
                    self.logger.info("Thi truong co phieu My dang dong cua (Market Closed)")
                    if not self.order_manager.dry_run:
                        return
            except Exception as e:
                self.logger.warning("Khong lay duoc market clock: %s", e)

        for symbol in self.config.symbols:
            try:
                position = self.portfolio_manager.get_position_details(symbol)
            except RuntimeError as e:
                self.logger.error("Bo qua %s vi khong kiem tra duoc stop-loss: %s",
                                  symbol, e)
                continue

            if position is not None and position["unrealized_plpc"] <= -self.config.stop_loss_pct:
                loss_pct = position["unrealized_plpc"] * 100
                self.logger.warning(
                    "STOP-LOSS %s: P/L %.2f%% <= -%.2f%%; ban toan bo vi the",
                    symbol, loss_pct, self.config.stop_loss_pct * 100)
                self.order_manager.place_market_order(
                    symbol, "sell", qty=abs(position["qty"]))
                # Do not open a new position in the same cycle after cutting a loss.
                continue

            data = self.data_manager.get_historical_data(symbol, self.config.history_days)
            if data.empty:
                continue
            self._log_market_snapshot(symbol, data)
            signals: List[TradingSignal] = []
            for strategy in self.strategies:
                for s in strategy.generate_signals(data, symbol):
                    self.logger.info(
                        "[%s] %s %s conf=%.2f signal_price=%.8f signal_at=%s | %s",
                        strategy.name, s.action, symbol, s.confidence, s.price,
                        s.timestamp.astimezone().isoformat(), s.reason)
                    signals.append(s)
            self._process_signals(symbol, signals)

    def _log_market_snapshot(self, symbol: str, data) -> None:
        """Log the latest Alpaca candle and indicator inputs for chart review."""
        bar = data.iloc[-1]
        bar_time = data.index[-1]
        bar_time_str = bar_time.isoformat() if hasattr(bar_time, "isoformat") else str(bar_time)
        close = data["close"]
        rsi = wilder_rsi(close, 14).iloc[-1]
        sma10 = simple_moving_average(close, 10).iloc[-1]
        sma30 = simple_moving_average(close, 30).iloc[-1]

        def fmt(value, digits=8):
            return "n/a" if pd.isna(value) else f"{float(value):.{digits}f}"

        self.logger.info(
            "MARKET logged_at_local=%s symbol=%s timeframe=1Min bar_at=%s bars=%s "
            "OHLCV=(%s,%s,%s,%s,%s) RSI14_WilderRMA_Close=%s SMA10_Close=%s SMA30_Close=%s",
            datetime.now().astimezone().isoformat(), symbol, bar_time_str, len(data),
            fmt(bar["open"]), fmt(bar["high"]),
            fmt(bar["low"]), fmt(bar["close"]), fmt(bar["volume"]),
            fmt(rsi, 4), fmt(sma10), fmt(sma30))

    def _process_signals(self, symbol: str, signals: List[TradingSignal]) -> None:
        if not signals:
            return
        groups: Dict[str, List[TradingSignal]] = defaultdict(list)
        for s in signals:
            groups[s.action].append(s)
        # Neu BUY va SELL xung dot: chi lay nhom co confidence trung binh cao hon
        action = max(groups, key=lambda a: sum(x.confidence for x in groups[a]) / len(groups[a]))
        self.execute_signal_group(symbol, action, groups[action])

    def execute_signal_group(self, symbol: str, action: str, signals: List[TradingSignal]) -> bool:
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        if avg_confidence < self.config.min_confidence:
            self.logger.info("Skipping %s for %s due to low confidence", action, symbol)
            return False
        current_qty = self.portfolio_manager.get_positions().get(
            symbol.replace("/", "").upper(), 0)
        if action == "BUY" and current_qty <= 0:
            notional = self.portfolio_manager.calculate_order_notional()
            if notional <= 0:
                return False
            return self.order_manager.place_market_order(
                symbol, "buy", notional=notional)
        if action == "SELL" and current_qty > 0:
            return self.order_manager.place_market_order(
                symbol, "sell", qty=abs(float(current_qty)))
        self.logger.info("Bo qua %s %s (vi the hien tai: %s)", action, symbol, current_qty)
        return False

    def run_continuous(self, interval_minutes: int = 5) -> None:
        self.logger.info("Crypto bot chay lien tuc (PAPER) moi %d phut. Symbols=%s",
                         interval_minutes, self.config.symbols)
        while True:
            try:
                self.run_trading_cycle()
                self.logger.info("Report: %s", self.generate_performance_report())
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.logger.error("Loi trong chu ky: %s", e)
            time.sleep(interval_minutes * 60)

    @staticmethod
    def _day_gain(account) -> float:
        """Bien dong equity so voi moc equity truoc do cua Alpaca."""
        return float(account.equity) - float(account.last_equity)

    def generate_performance_report(self) -> dict:
        positions = self.portfolio_manager.get_positions()
        account = self.api.get_account()
        return {
            "total_equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "positions": len(positions),
            "day_gain": self._day_gain(account),
        }
