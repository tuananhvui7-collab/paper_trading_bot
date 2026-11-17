import logging


class OrderManager:
    """Gui lenh market / limit."""

    def __init__(self, api, dry_run: bool = False):
        self.api, self.dry_run = api, dry_run
        self.logger = logging.getLogger("TradingBot.orders")

    def place_market_order(self, symbol: str, qty: int, side: str) -> bool:
        if self.dry_run:
            self.logger.info("[DRY-RUN] %s %d %s (market)", side, qty, symbol)
            return True
        try:
            order = self.api.submit_order(symbol=symbol, qty=qty, side=side,
                                          type="market", time_in_force="day")
            self.logger.info("Market %s %d %s -> order %s", side, qty, symbol, order.id)
            return True
        except Exception as e:
            self.logger.error("Loi dat lenh market %s %s: %s", side, symbol, e)
            return False

    def place_limit_order(self, symbol: str, qty: int, side: str, limit_price: float) -> bool:
        if self.dry_run:
            self.logger.info("[DRY-RUN] %s %d %s @ %.2f (limit)", side, qty, symbol, limit_price)
            return True
        try:
            order = self.api.submit_order(symbol=symbol, qty=qty, side=side, type="limit",
                                          time_in_force="day", limit_price=limit_price)
            self.logger.info("Limit %s %d %s @ %.2f -> order %s", side, qty, symbol,
                             limit_price, order.id)
            return True
        except Exception as e:
            self.logger.error("Loi dat lenh limit %s %s: %s", side, symbol, e)
            return False
