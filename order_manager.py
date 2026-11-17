import logging


class OrderManager:
    """Gui lenh market / limit."""

    def __init__(self, api, dry_run: bool = False):
        self.api, self.dry_run = api, dry_run
        self.logger = logging.getLogger("TradingBot.orders")

    def place_market_order(self, symbol: str, side: str, qty: float = None,
                           notional: float = None) -> bool:
        if (qty is None) == (notional is None):
            raise ValueError("Can truyen dung mot trong hai: qty hoac notional")
        if self.dry_run:
            amount = f"{qty} {symbol.split('/')[0]}" if qty is not None else f"${notional:.2f}"
            self.logger.info("[DRY-RUN] %s %s (crypto market)", side, amount)
            return True
        try:
            params = {"symbol": symbol, "side": side, "type": "market",
                      "time_in_force": "gtc"}
            if qty is not None:
                params["qty"] = qty
            else:
                params["notional"] = notional
            order = self.api.submit_order(**params)
            self.logger.info("Crypto market %s %s -> order %s", side, symbol, order.id)
            return True
        except Exception as e:
            self.logger.error("Loi dat lenh market %s %s: %s", side, symbol, e)
            return False

    def place_limit_order(self, symbol: str, qty: float, side: str, limit_price: float) -> bool:
        if self.dry_run:
            self.logger.info("[DRY-RUN] %s %g %s @ %.2f (crypto limit)",
                             side, qty, symbol, limit_price)
            return True
        try:
            order = self.api.submit_order(symbol=symbol, qty=qty, side=side, type="limit",
                                          time_in_force="gtc", limit_price=limit_price)
            self.logger.info("Crypto limit %s %g %s @ %.2f -> order %s", side, qty, symbol,
                             limit_price, order.id)
            return True
        except Exception as e:
            self.logger.error("Loi dat lenh limit %s %s: %s", side, symbol, e)
            return False
