import logging


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("trading_bot.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )
    return logging.getLogger("TradingBot")
