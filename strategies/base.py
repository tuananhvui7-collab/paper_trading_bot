from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from models import TradingSignal


class TradingStrategy(ABC):
    """Strategy Pattern: moi thuat toan giao dich ke thua lop nay."""

    def __init__(self, name: str, default_quantity: int = 1):
        self.name = name
        self.default_quantity = default_quantity

    def _calculate_quantity(self, price: float) -> int:
        # So luong that se do PortfolioManager tinh lai khi thuc thi.
        return self.default_quantity

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        pass
