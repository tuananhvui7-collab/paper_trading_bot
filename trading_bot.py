import logging
import time
from collections import defaultdict
from typing import Dict, List

import alpaca_trade_api as tradeapi

from config import PAPER_BASE_URL, TradingConfig
from data_manager import DataManager
from models import TradingSignal
from order_manager import OrderManager
from portfolio_manager import PortfolioManager
from strategies.bollinger import BollingerBandsStrategy
from strategies.ma_crossover import MovingAverageCrossoverStrategy
from strategies.rsi import RSIStrategy


class TradingBot:
    """Dieu phoi: DataManager + Strategies + PortfolioManager + OrderManager."""

    def __init__(self, config: TradingConfig, api=None, dry_run: bool = False,
                 use_bollinger: bool = False, ignore_market_hours: bool = False):
        config.validate()
        self.config = config
        self.logger = logging.getLogger("TradingBot")
        self.ignore_market_hours = ignore_market_hours
        # 1) cau hinh -> 2) ket noi API (luon paper) -> 3) component -> 4) strategies
        self.api = api or tradeapi.REST(config.api_key, config.api_secret,
                                        base_url=PAPER_BASE_URL, api_version="v2")
        self.data_manager = DataManager(self.api, feed=config.data_feed)
        self.portfolio_manager = PortfolioManager(self.api, config)
        self.order_manager = OrderManager(self.api, dry_run=dry_run)
        self.strategies = [MovingAverageCrossoverStrategy(), RSIStrategy()]
        if use_bollinger:
            self.strategies.append(BollingerBandsStrategy())

    # ---- chu ky giao dich ----
    def is_market_open(self) -> bool:
        try:
            return bool(self.api.get_clock().is_open)
        except Exception as e:
            self.logger.error("Khong kiem tra duoc gio thi truong: %s", e)
            return False

    def run_trading_cycle(self) -> None:
        if not self.ignore_market_hours and not self.is_market_open():
            self.logger.info("Thi truong dong cua - tam dung giao dich")
            return
        for symbol in self.config.symbols:
            data = self.data_manager.get_historical_data(symbol, self.config.history_days)
            if data.empty:
                continue
            signals: List[TradingSignal] = []
            for strategy in self.strategies:
                for s in strategy.generate_signals(data, symbol):
                    self.logger.info("[%s] %s %s conf=%.2f | %s", strategy.name, s.action,
                                     symbol, s.confidence, s.reason)
                    signals.append(s)
            self._process_signals(symbol, signals)

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
        current_qty = self.portfolio_manager.get_positions().get(symbol, 0)
        price = signals[0].price
        if action == "BUY" and current_qty <= 0:
            qty = self.portfolio_manager.calculate_position_size(price)
            if qty < 1:
                return False
            return self.order_manager.place_market_order(symbol, qty, "buy")
        if action == "SELL" and current_qty > 0:
            return self.order_manager.place_market_order(symbol, int(current_qty), "sell")
        self.logger.info("Bo qua %s %s (vi the hien tai: %s)", action, symbol, current_qty)
        return False

    def run_continuous(self, interval_minutes: int = 30) -> None:
        self.logger.info("Bot chay lien tuc (PAPER) moi %d phut. Symbols=%s",
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
        """Bai dung account.unrealized_pl; neu tai khoan khong co truong nay thi dung equity - last_equity."""
        value = getattr(account, "unrealized_pl", None)
        if value is None:
            value = float(account.equity) - float(account.last_equity)
        return float(value)

    def generate_performance_report(self) -> dict:
        positions = self.portfolio_manager.get_positions()
        account = self.api.get_account()
        return {
            "total_equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "positions": len(positions),
            "day_gain": self._day_gain(account),
        }
