from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradingSignal:
    symbol: str
    action: str          # "BUY" | "SELL"
    price: float
    quantity: int
    timestamp: datetime
    reason: str
    confidence: float    # 0..1
