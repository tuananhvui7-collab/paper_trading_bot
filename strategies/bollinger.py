"""Vi du 'Adding New Trading Strategies' trong bai (bai de trong phan logic)."""
from datetime import datetime
from typing import List

import pandas as pd

from models import TradingSignal
from .base import TradingStrategy


class BollingerBandsStrategy(TradingStrategy):
    def __init__(self, period: int = 20, std_dev: float = 2):
        super().__init__("BollingerBands")
        self.period, self.std_dev = period, std_dev

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        if len(data) < self.period + 1:
            return []
        close = data["close"]
        mid = close.rolling(self.period).mean().iloc[-1]
        sd = close.rolling(self.period).std().iloc[-1]
        upper, lower = mid + self.std_dev * sd, mid - self.std_dev * sd
        price = float(close.iloc[-1])
        if price < lower:
            action, why = "BUY", f"Gia {price:.2f} < dai duoi {lower:.2f}"
        elif price > upper:
            action, why = "SELL", f"Gia {price:.2f} > dai tren {upper:.2f}"
        else:
            return []
        return [TradingSignal(symbol=symbol, action=action, price=price,
                              quantity=self._calculate_quantity(price),
                              timestamp=datetime.now(), reason=why, confidence=0.6)]
