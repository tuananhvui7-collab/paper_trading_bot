import argparse
import os

from dotenv import load_dotenv

from config import TradingConfig
from logging_setup import setup_logging
from trading_bot import TradingBot


def main() -> None:
    p = argparse.ArgumentParser(description="Alpaca paper trading bot")
    p.add_argument("--once", action="store_true", help="chay 1 chu ky roi thoat")
    p.add_argument("--dry-run", action="store_true", help="chi log, khong gui lenh")
    p.add_argument("--interval", type=int, default=30, help="so phut giua cac chu ky")
    p.add_argument("--bollinger", action="store_true", help="bat them chien luoc Bollinger")
    p.add_argument("--ignore-market-hours", action="store_true")
    args = p.parse_args()

    load_dotenv()
    log = setup_logging()
    symbols = [s.strip().upper() for s in os.getenv("SYMBOLS", "").split(",") if s.strip()] or None
    config = TradingConfig(api_key=os.getenv("ALPACA_API_KEY", ""),
                           api_secret=os.getenv("ALPACA_API_SECRET", ""), symbols=symbols)
    bot = TradingBot(config, dry_run=args.dry_run, use_bollinger=args.bollinger,
                     ignore_market_hours=args.ignore_market_hours)
    try:
        if args.once:
            bot.run_trading_cycle()
            log.info("Report: %s", bot.generate_performance_report())
        else:
            bot.run_continuous(interval_minutes=args.interval)
    except KeyboardInterrupt:
        log.info("Da dung bot.")


if __name__ == "__main__":
    main()
