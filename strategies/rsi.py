from datetime import datetime
from typing import List

import pandas as pd

from models import TradingSignal
from .base import TradingStrategy


class RSIStrategy(TradingStrategy):
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI")
        self.period, self.oversold, self.overbought = period, oversold, overbought

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.where(loss != 0, 100.0).where(gain.notna())  # loss=0 -> RSI 100

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        if len(data) < self.period + 2:
            return []
        rsi = self._calculate_rsi(data["close"], self.period).iloc[-1]
        if pd.isna(rsi):
            return []
        price = float(data["close"].iloc[-1])
        if rsi < self.oversold:
            action, why = "BUY", f"RSI={rsi:.1f} < {self.oversold} (oversold)"
            conf = 0.8 if rsi < self.oversold - 10 else 0.65
        elif rsi > self.overbought:
            action, why = "SELL", f"RSI={rsi:.1f} > {self.overbought} (overbought)"
            conf = 0.8 if rsi > self.overbought + 10 else 0.65
        else:
            return []
        return [TradingSignal(symbol=symbol, action=action, price=price,
                              quantity=self._calculate_quantity(price),
                              timestamp=datetime.now(), reason=why, confidence=conf)]
