from datetime import datetime
from typing import List

import pandas as pd

from models import TradingSignal
from .base import TradingStrategy
from .indicators import simple_moving_average


class MovingAverageCrossoverStrategy(TradingStrategy):
    def __init__(self, short_window: int = 10, long_window: int = 30):
        super().__init__("MovingAverageCrossover")
        if short_window >= long_window:
            raise ValueError("short_window phai < long_window")
        self.short_window, self.long_window = short_window, long_window

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        if len(data) < self.long_window + 2:
            return []
        close = data["close"]
        ma_short = simple_moving_average(close, self.short_window)
        ma_long = simple_moving_average(close, self.long_window)
        price = float(close.iloc[-1])
        signals: List[TradingSignal] = []

        if ma_short.iloc[-1] > ma_long.iloc[-1] and ma_short.iloc[-2] <= ma_long.iloc[-2]:
            signals.append(TradingSignal(
                symbol=symbol, action="BUY", price=price,
                quantity=self._calculate_quantity(price), timestamp=datetime.now(),
                reason=f"SMA crossover: {ma_short.iloc[-1]:.2f} > {ma_long.iloc[-1]:.2f}",
                confidence=0.7))
        elif ma_short.iloc[-1] < ma_long.iloc[-1] and ma_short.iloc[-2] >= ma_long.iloc[-2]:
            signals.append(TradingSignal(
                symbol=symbol, action="SELL", price=price,
                quantity=self._calculate_quantity(price), timestamp=datetime.now(),
                reason=f"SMA crossover: {ma_short.iloc[-1]:.2f} < {ma_long.iloc[-1]:.2f}",
                confidence=0.7))
        return signals
