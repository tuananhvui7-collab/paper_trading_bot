from datetime import datetime
from typing import List

import pandas as pd

from models import TradingSignal
from .base import TradingStrategy


class MovingAverageCrossoverStrategy(TradingStrategy):
    def __init__(self, short_window: int = 10, long_window: int = 30):
        super().__init__("MovingAverageCrossover")
        if short_window >= long_window:
            raise ValueError("short_window phai < long_window")
        self.short_window, self.long_window = short_window, long_window

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        if len(data) < self.long_window + 2:
            return []
        df = data.copy()
        df["MA_short"] = df["close"].rolling(self.short_window).mean()
        df["MA_long"] = df["close"].rolling(self.long_window).mean()
        latest, previous = df.iloc[-1], df.iloc[-2]
        price = float(latest["close"])
        signals: List[TradingSignal] = []

        if latest["MA_short"] > latest["MA_long"] and previous["MA_short"] <= previous["MA_long"]:
            signals.append(TradingSignal(
                symbol=symbol, action="BUY", price=price,
                quantity=self._calculate_quantity(price), timestamp=datetime.now(),
                reason=f"MA crossover: {latest['MA_short']:.2f} > {latest['MA_long']:.2f}",
                confidence=0.7))
        elif latest["MA_short"] < latest["MA_long"] and previous["MA_short"] >= previous["MA_long"]:
            signals.append(TradingSignal(
                symbol=symbol, action="SELL", price=price,
                quantity=self._calculate_quantity(price), timestamp=datetime.now(),
                reason=f"MA crossover: {latest['MA_short']:.2f} < {latest['MA_long']:.2f}",
                confidence=0.7))
        return signals
