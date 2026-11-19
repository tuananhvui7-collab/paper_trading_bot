"""main.py: Entrypoint cho Alpaca Paper Trading Bot & Stock Screening."""
import argparse
import os

from dotenv import load_dotenv

from config import TradingConfig
from data_manager import DataManager
from logging_setup import setup_logging
from stock_screener import StockScreener
from trading_bot import TradingBot


def main() -> None:
    p = argparse.ArgumentParser(description="Alpaca Paper Trading Bot & Stock Screener")
    p.add_argument("--once", action="store_true", help="chạy 1 chu kỳ rồi thoát")
    p.add_argument("--dry-run", action="store_true", help="chỉ log tính toán, không gửi lệnh lên sàn")
    p.add_argument("--interval", type=int, default=5, help="số phút giữa các chu kỳ")
    p.add_argument("--bollinger", action="store_true", help="bật thêm chiến lược Bollinger Bands")
    p.add_argument("--stocks", action="store_true", help="chạy ở chế độ cổ phiếu Mỹ (mặc định dùng sàn IEX)")
    p.add_argument("--screen", action="store_true", help="chạy bộ lọc Stock Screener trước khi khởi động Bot")
    args = p.parse_args()

    load_dotenv()
    log = setup_logging()

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    raw_symbols = os.getenv("SYMBOLS", "")
    env_symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()] or None

    is_crypto = False if args.stocks else (True if (env_symbols and any("/" in s for s in env_symbols)) else None)

    config = TradingConfig(
        api_key=api_key,
        api_secret=api_secret,
        symbols=env_symbols,
        is_crypto=is_crypto,
    )

    # Chạy quy trình Stock Screening nếu có cờ --screen
    if args.screen:
        log.info("--- KÍCH HOẠT QUY TRÌNH HISTORICAL DATA-BASED STOCK SCREENING ---")
        import alpaca_trade_api as tradeapi
        from config import PAPER_BASE_URL
        api = tradeapi.REST(api_key, api_secret, base_url=PAPER_BASE_URL, api_version="v2")
        dm = DataManager(api, feed=config.data_feed)
        screener = StockScreener(dm, config)
        result = screener.run_screening()

        log.info("\n=== BẢNG CHỈ SỐ TÀI CHÍNH & TRẠNG THÁI SÀNG LỌC ===\n%s",
                 result.summary_df[["Symbol", "Data Status", "ADV ($)", "Annual Volatility", "Max Correlation", "Screening Status"]])

        if not result.correlation_matrix.empty:
            log.info("\n=== MA TRẬN TƯƠNG QUAN PEARSON (CORRELATION MATRIX) ===\n%s",
                     result.correlation_matrix.to_string())

            # Quét và cảnh báo các cặp có tương quan cao
            high_corr_pairs = []
            cols = list(result.correlation_matrix.columns)
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    val = result.correlation_matrix.iloc[i, j]
                    if val > config.max_correlation:
                        high_corr_pairs.append((cols[i], cols[j], val))

            if high_corr_pairs:
                log.info("\n=== CẢNH BÁO TƯƠNG QUAN CAO (r > %.2f) ===", config.max_correlation)
                for c1, c2, val in high_corr_pairs:
                    log.warning("Cặp [%s - %s] có tương quan r = %.2f > %.2f (trùng lặp rủi ro ngành)",
                                c1, c2, val, config.max_correlation)

        if result.selected_symbols:
            log.info("\n=== KẾT QUẢ SÀNG LỌC CUỐI CÙNG ===")
            log.info("Mã được chọn sau sàng lọc (Top %d): %s", config.target_top_n, result.selected_symbols)
            config.symbols = result.selected_symbols
        else:
            log.warning("Không có mã nào đạt toàn bộ tiêu chí! Giữ nguyên danh mục mặc định.")

    log.info("Khởi động TradingBot với danh sách symbols = %s (is_crypto=%s)", config.symbols, config.is_crypto)
    bot = TradingBot(config, dry_run=args.dry_run, use_bollinger=args.bollinger)

    try:
        if args.once:
            bot.run_trading_cycle()
            log.info("Report: %s", bot.generate_performance_report())
        else:
            bot.run_continuous(interval_minutes=args.interval)
    except KeyboardInterrupt:
        log.info("Đã dừng bot.")


if __name__ == "__main__":
    main()
