"""TradingConfig: tap trung toan bo cai dat (Configuration Pattern trong bai viet)."""
from dataclasses import dataclass
from typing import List, Optional

PAPER_BASE_URL = "https://paper-api.alpaca.markets"  # luon la paper trading


@dataclass
class TradingConfig:
    api_key: str
    api_secret: str
    max_position_size: float = 1000.0   # toi da $ cho moi lenh
    risk_per_trade: float = 0.02        # 2% buying power
    symbols: Optional[List[str]] = None
    min_confidence: float = 0.5         # nguong loc tin hieu
    history_days: int = 100
    data_feed: Optional[str] = "iex"   # "iex" (goi mien phi) | "sip" (tra phi) | None = mac dinh cua Alpaca

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]

    def validate(self) -> None:
        """'Validate configuration' trong muc Paper Trading Safety."""
        if not self.api_key or not self.api_secret:
            raise ValueError("Thieu ALPACA_API_KEY / ALPACA_API_SECRET")
        if not 0 < self.risk_per_trade <= 0.05:
            raise ValueError("risk_per_trade nen trong (0, 0.05]")
        if self.max_position_size <= 0:
            raise ValueError("max_position_size phai > 0")
        if not self.symbols:
            raise ValueError("Danh sach symbols rong")
