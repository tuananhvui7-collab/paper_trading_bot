"""TradingConfig: tap trung toan bo cai dat (Configuration Pattern trong bai viet)."""
from dataclasses import dataclass
from typing import List, Optional

PAPER_BASE_URL = "https://paper-api.alpaca.markets"


@dataclass
class TradingConfig:
    api_key: str
    api_secret: str
    max_position_size: float = 1000.0   # USD notional cap per buy
    risk_per_trade: float = 0.02        # order budget as a fraction of buying power
    stop_loss_pct: float = 0.20         # close position at a 20% unrealized loss
    symbols: Optional[List[str]] = None
    min_confidence: float = 0.5         # nguong loc tin hieu
    history_days: int = 5               # warm-up history for 1-minute indicators
    is_crypto: Optional[bool] = None    # True: crypto, False: stocks, None: auto-detect
    data_feed: str = "iex"              # "iex" (free tier) | "sip" (paid tier)

    # --- Tham so cho Historical Data-based Stock Screening ---
    screening_universe: Optional[List[str]] = None
    screening_lookback_days: int = 60   # ~3 thang giao dich de danh gia on dinh
    min_adv: float = 200000.0           # $200k USD Average Dollar Volume tren IEX
    min_volatility: float = 0.15        # 15%/nam (tuong duong S&P 500)
    max_volatility: float = 0.65        # 65%/nam (chan co phieu rac bien dong dot bien)
    max_correlation: float = 0.75       # Loai bo cac ma co tuong quan > 0.75
    target_top_n: int = 3               # So luong ma toi da dua vao TradingBot sau loc

    def __post_init__(self):
        if self.symbols is None:
            if self.is_crypto is False:
                self.symbols = ["AAPL", "MSFT", "GOOGL"]
            else:
                self.symbols = ["BTC/USD", "ETH/USD"]

        # Tu dong nhan dien che do Crypto neu chua chi dinh
        if self.is_crypto is None:
            self.is_crypto = any("/" in s for s in self.symbols)

        # Khoi tao vu tru sang loc mac dinh neu chua truyen
        if self.screening_universe is None:
            if self.is_crypto:
                self.screening_universe = ["BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "DOGE/USD"]
            else:
                self.screening_universe = [
                    "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA",
                    "JPM", "BAC", "XOM", "CVX", "JNJ"
                ]

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
            raise ValueError("Danh sach symbols rong")
        if self.is_crypto and any("/" not in symbol for symbol in self.symbols):
            raise ValueError("Crypto symbols phai co dang BTC/USD")
        if self.min_volatility >= self.max_volatility:
            raise ValueError("min_volatility phai nho hon max_volatility")
        if not 0 < self.max_correlation <= 1.0:
            raise ValueError("max_correlation phai trong khoang (0, 1]")
        if self.min_adv <= 0:
            raise ValueError("min_adv phai > 0")
