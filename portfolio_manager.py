import logging
from typing import Dict, Optional

from config import TradingConfig


class PortfolioManager:
    """Quan ly vi the va tinh toan rui ro."""

    def __init__(self, api, config: TradingConfig):
        self.api, self.config = api, config
        self.logger = logging.getLogger("TradingBot.portfolio")

    def get_positions(self) -> Dict[str, float]:
        try:
            # Alpaca has used both BTC/USD and BTCUSD symbology in crypto APIs.
            return {p.symbol.replace("/", "").upper(): float(p.qty)
                    for p in self.api.list_positions()}
        except Exception as e:
            self.logger.error("Loi lay vi the: %s", e)
            # Do not treat an API failure as an empty portfolio and buy again.
            raise RuntimeError("Khong lay duoc vi the; bo qua giao dich") from e

    def get_position_details(self, symbol: str) -> Optional[dict]:
        """Return crypto quantity and Alpaca's unrealized P/L fraction."""
        wanted = symbol.replace("/", "").upper()
        try:
            for position in self.api.list_positions():
                actual = position.symbol.replace("/", "").upper()
                if actual == wanted:
                    pnl_pct = getattr(position, "unrealized_plpc", None)
                    if pnl_pct is None:
                        raise RuntimeError(
                            f"Alpaca khong tra unrealized_plpc cho {symbol}")
                    return {
                        "qty": float(position.qty),
                        "unrealized_plpc": float(pnl_pct),
                    }
            return None
        except Exception as e:
            self.logger.error("Loi lay P/L vi the %s: %s", symbol, e)
            raise RuntimeError(
                f"Khong the kiem tra stop-loss cho {symbol}") from e

    def get_buying_power(self) -> float:
        return float(self.api.get_account().buying_power)

    def calculate_order_notional(self, risk_amount: Optional[float] = None) -> float:
        """USD amount for a crypto buy; this is exposure, not maximum possible loss."""
        if risk_amount is None:
            buying_power = self.get_buying_power()
            risk_amount = min(buying_power * self.config.risk_per_trade,
                              self.config.max_position_size)
        if risk_amount <= 0:
            self.logger.warning("Notional mua crypto khong hop le: %.2f", risk_amount)
            return 0.0
        return round(float(risk_amount), 2)
