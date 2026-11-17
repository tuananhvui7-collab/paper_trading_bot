"""TradingConfig: tap trung toan bo cai dat (Configuration Pattern trong bai viet)."""
from dataclasses import dataclass
from typing import List, Optional

PAPER_BASE_URL = "https://paper-api.alpaca.markets"  # crypto paper trading only


@dataclass
class TradingConfig:
    api_key: str
    api_secret: str
    max_position_size: float = 1000.0   # USD notional cap per buy
    risk_per_trade: float = 0.02        # order budget as a fraction of buying power
    stop_loss_pct: float = 0.20         # close position at a 20% unrealized loss
    symbols: Optional[List[str]] = None
    min_confidence: float = 0.5         # nguong loc tin hieu
    history_days: int = 100

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BTC/USD", "ETH/USD"]

    def validate(self) -> None:
        """'Validate configuration' trong muc Paper Trading Safety."""
        if not self.api_key or not self.api_secret:
            raise ValueError("Thieu ALPACA_API_KEY / ALPACA_API_SECRET")
        if not 0 < self.risk_per_trade <= 0.05:
            raise ValueError("risk_per_trade nen trong (0, 0.05]")
        if self.max_position_size <= 0:
            raise ValueError("max_position_size phai > 0")
        if not 0 < self.stop_loss_pct < 1:
            raise ValueError("stop_loss_pct phai trong khoang (0, 1)")
        if not self.symbols:
            raise ValueError("Danh sach cap crypto rong")
        if any("/" not in symbol for symbol in self.symbols):
            raise ValueError("Crypto symbols phai co dang BTC/USD")
