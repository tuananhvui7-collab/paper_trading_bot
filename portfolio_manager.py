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
            return {p.symbol: float(p.qty) for p in self.api.list_positions()}
        except Exception as e:
            self.logger.error("Loi lay vi the: %s", e)
            return {}

    def get_buying_power(self) -> float:
        return float(self.api.get_account().buying_power)

    def calculate_position_size(self, price: float, risk_amount: Optional[float] = None) -> int:
        if risk_amount is None:
            buying_power = self.get_buying_power()
            risk_amount = min(buying_power * self.config.risk_per_trade,
                              self.config.max_position_size)
            if price > buying_power:
                self.logger.warning("Gia %.2f vuot buying power %.2f", price, buying_power)
                return 0
        return max(1, int(risk_amount / price))
