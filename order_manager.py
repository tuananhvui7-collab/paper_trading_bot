import logging
import time


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
            order_id = str(order.id)
            self.logger.info("ORDER SUBMITTED side=%s symbol=%s order_id=%s status=%s",
                             side, symbol, order_id, getattr(order, "status", "unknown"))
            self._log_fill_when_available(order, symbol, side)
            return True
        except Exception as e:
            self.logger.error("Loi dat lenh market %s %s: %s", side, symbol, e)
            return False

    def _log_fill_when_available(self, order, symbol: str, side: str) -> None:
        """Poll briefly so the log captures Alpaca's actual average fill price."""
        order_id = str(order.id)
        status = {"filled", "canceled", "expired", "rejected"}
        latest = order
        deadline = time.monotonic() + 5
        get_order = getattr(self.api, "get_order", None)
        while callable(get_order) and getattr(latest, "status", None) not in status:
            if time.monotonic() >= deadline:
                break
            time.sleep(0.5)
            try:
                latest = get_order(order_id)
            except Exception as e:
                self.logger.warning("ORDER STATUS unavailable order_id=%s: %s", order_id, e)
                break

        order_status = getattr(latest, "status", "unknown")
        avg_price = getattr(latest, "filled_avg_price", None)
        filled_at = getattr(latest, "filled_at", None)
        filled_qty = getattr(latest, "filled_qty", None)
        if avg_price:
            self.logger.info(
                "ORDER FILL side=%s symbol=%s order_id=%s status=%s "
                "filled_qty=%s avg_fill_price=%s filled_at_utc=%s",
                side, symbol, order_id, order_status, filled_qty, avg_price, filled_at)
        else:
            self.logger.info("ORDER UPDATE side=%s symbol=%s order_id=%s status=%s "
                             "filled_qty=%s avg_fill_price=pending",
                             side, symbol, order_id, order_status, filled_qty)

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
