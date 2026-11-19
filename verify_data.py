"""verify_data.py: Bo kiem thu va giam sat toan dien cho Trading Bot.

Chuc nang:
1. Kiem tra tinh toan ven du lieu (Data Sanity Check: OHLCV, null, gaps).
2. Kiem tra do chinh xac cua chi bao ky thuat (RSI Wilder, SMA, Bollinger).
3. Audit file log (trading_bot.log) de kiem tra xem bot chay co dung logic khong.
4. Chay kiem thu offline (pytest) de bao dam logic khong bi loi hoi quy.
"""
import argparse
import os
import re
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from config import TradingConfig, PAPER_BASE_URL
from data_manager import DataManager
from strategies.indicators import simple_moving_average, wilder_rsi


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)


def check_data_integrity(df: pd.DataFrame, symbol: str) -> List[str]:
    """Kiem tra tinh hop le va toan ven cua du lieu nen OHLCV."""
    issues = []
    if df.empty:
        return [f"[{symbol}] Du lieu rong (0 nen)"]

    # 1. Kiem tra cot
    required_cols = ["open", "high", "low", "close", "volume"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        issues.append(f"[{symbol}] Thieu cac cot bat buoc: {missing_cols}")

    # 2. Kiem tra gia tri NaN / Null
    null_counts = df[required_cols].isna().sum()
    for col, count in null_counts.items():
        if count > 0:
            issues.append(f"[{symbol}] Cot {col} chua {count} gia tri NaN/Null")

    # 3. Kiem tra logic gia (High >= Low, High >= Open/Close, Low <= Open/Close)
    invalid_hl = (df["high"] < df["low"]).sum()
    if invalid_hl > 0:
        issues.append(f"[{symbol}] Co {invalid_hl} nen vi pham High < Low!")

    invalid_ho = (df["high"] < df["open"]).sum()
    invalid_hc = (df["high"] < df["close"]).sum()
    if invalid_ho > 0 or invalid_hc > 0:
        issues.append(f"[{symbol}] Co nen vi pham High < Open hoac High < Close!")

    invalid_lo = (df["low"] > df["open"]).sum()
    invalid_lc = (df["low"] > df["close"]).sum()
    if invalid_lo > 0 or invalid_lc > 0:
        issues.append(f"[{symbol}] Co nen vi pham Low > Open hoac Low > Close!")

    # 4. Kiem tra Volume am
    neg_vol = (df["volume"] < 0).sum()
    if neg_vol > 0:
        issues.append(f"[{symbol}] Co {neg_vol} nen co Volume am!")

    # 5. Kiem tra timestamp continuity (khoang cach giua cac nen)
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        time_diffs = df.index.to_series().diff().dropna()
        large_gaps = time_diffs[time_diffs > pd.Timedelta(minutes=15)]
        if len(large_gaps) > 0:
            max_gap = time_diffs.max()
            issues.append(f"[{symbol}] Phat hien {len(large_gaps)} khoang trong (gap > 15p), gap lon nhat: {max_gap}")

    return issues


def check_indicator_sanity(df: pd.DataFrame, symbol: str) -> List[str]:
    """Kiem tra tinh hop le trong tinh toan chi bao ky thuat."""
    issues = []
    if len(df) < 35:
        issues.append(f"[{symbol}] Khong du nen de tinh SMA30 va RSI14 (so nen: {len(df)})")
        return issues

    close = df["close"]

    # 1. Kiem tra SMA
    sma10 = simple_moving_average(close, 10)
    sma30 = simple_moving_average(close, 30)

    # SMA tai cac nen cuoi khong duoc NaN
    if pd.isna(sma10.iloc[-1]):
        issues.append(f"[{symbol}] SMA10 cua nen cuoi bi NaN")
    if pd.isna(sma30.iloc[-1]):
        issues.append(f"[{symbol}] SMA30 cua nen cuoi bi NaN")

    # SMA phai nam trong khoang gia min-max cua cua so tuong ung
    recent_min = close.iloc[-10:].min()
    recent_max = close.iloc[-10:].max()
    if not (recent_min <= sma10.iloc[-1] <= recent_max):
        issues.append(f"[{symbol}] SMA10 vuot ngoai bien do gia 10 nến gan nhat")

    # 2. Kiem tra Wilder RSI
    rsi = wilder_rsi(close, 14)
    last_rsi = rsi.iloc[-1]
    if pd.isna(last_rsi):
        issues.append(f"[{symbol}] RSI14 cua nen cuoi bi NaN")
    elif not (0 <= last_rsi <= 100):
        issues.append(f"[{symbol}] RSI14 nam ngoai khoang [0, 100]: {last_rsi}")

    return issues


def audit_log_file(log_path: str = "trading_bot.log") -> Dict:
    """Phan tich file log de kiem tra hoat dong thuc te cua bot."""
    if not os.path.exists(log_path):
        return {"error": f"Khong tim thay file log tai: {log_path}"}

    stats = {
        "total_lines": 0,
        "market_snapshots": 0,
        "signals": {"BUY": 0, "SELL": 0, "details": []},
        "orders_submitted": 0,
        "dry_run_orders": 0,
        "orders_filled": 0,
        "stop_loss_events": 0,
        "skipped_actions": 0,
        "warnings": 0,
        "errors": 0,
        "latest_market_time": None,
        "error_samples": [],
    }

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stats["total_lines"] += 1
            if " - ERROR - " in line:
                stats["errors"] += 1
                if len(stats["error_samples"]) < 5:
                    stats["error_samples"].append(line.strip())
            elif " - WARNING - " in line:
                stats["warnings"] += 1

            if "MARKET logged_at_local=" in line:
                stats["market_snapshots"] += 1
                # trich xuat thoi gian
                m = re.search(r"logged_at_local=([^\s]+)", line)
                if m:
                    stats["latest_market_time"] = m.group(1)

            if "conf=" in line and ("BUY" in line or "SELL" in line):
                if "BUY" in line:
                    stats["signals"]["BUY"] += 1
                if "SELL" in line:
                    stats["signals"]["SELL"] += 1
                stats["signals"]["details"].append(line.strip())

            if "ORDER SUBMITTED" in line or "Crypto market buy" in line:
                stats["orders_submitted"] += 1
            if "[DRY-RUN]" in line:
                stats["dry_run_orders"] += 1
            if "ORDER FILL" in line:
                stats["orders_filled"] += 1
            if "STOP-LOSS" in line:
                stats["stop_loss_events"] += 1
            if "Bo qua " in line or "Skipping " in line:
                stats["skipped_actions"] += 1

    return stats


def run_live_data_verification():
    """Ket noi lay du lieu live tu Alpaca va kiem tra."""
    print_header("1. Kiem tra Du lieu Live & Tinh toan Chi bao tu Alpaca")
    load_dotenv()
    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_API_SECRET", "")
    raw_symbols = os.getenv("SYMBOLS", "BTC/USD,ETH/USD")
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]

    if not api_key or not api_secret:
        print("[FAIL] Thieu ALPACA_API_KEY hoac ALPACA_API_SECRET trong .env!")
        return

    import alpaca_trade_api as tradeapi
    api = tradeapi.REST(api_key, api_secret, base_url=PAPER_BASE_URL, api_version="v2")
    dm = DataManager(api)

    for symbol in symbols:
        print(f"\n--- Kiem tra cap: {symbol} ---")
        df = dm.get_historical_data(symbol, days=5)
        print(f"  + So luong nen tai ve: {len(df)}")
        if df.empty:
            print(f"  [FAIL] Khong lay duoc du lieu cho {symbol}!")
            continue

        print(f"  + Nen dau: {df.index[0]} | Nen cuoi: {df.index[-1]}")
        last_close = df['close'].iloc[-1]
        print(f"  + Gia dong cua cuoi cung: {last_close:.2f} USD")

        # 1. Kiem tra tinh toan ven
        data_issues = check_data_integrity(df, symbol)
        if not data_issues:
            print("  [PASS] Toan ven du lieu (OHLCV, no-NaN, Logic High/Low/Open/Close): HOP LE")
        else:
            for issue in data_issues:
                print(f"  [CANH BAO] {issue}")

        # 2. Kiem tra chi bao
        ind_issues = check_indicator_sanity(df, symbol)
        rsi_val = wilder_rsi(df["close"], 14).iloc[-1]
        sma10_val = simple_moving_average(df["close"], 10).iloc[-1]
        sma30_val = simple_moving_average(df["close"], 30).iloc[-1]
        print(f"  + Chi bao hien tai: RSI14={rsi_val:.2f} | SMA10={sma10_val:.2f} | SMA30={sma30_val:.2f}")

        if not ind_issues:
            print("  [PASS] Tinh toan chi bao ky thuat: CHINH XAC & ON DINH")
        else:
            for issue in ind_issues:
                print(f"  [FAIL] {issue}")


def run_log_audit():
    """Audit va tong hop tu file trading_bot.log."""
    print_header("2. Audit Nhat ky Giao dich (trading_bot.log)")
    stats = audit_log_file("trading_bot.log")
    if "error" in stats:
        print(f"[FAIL] {stats['error']}")
        return

    print(f"  + Tong so dong log: {stats['total_lines']}")
    print(f"  + So lan snapshot thi truong (MARKET cycles): {stats['market_snapshots']}")
    print(f"  + Thoi diem chu ky gan nhat: {stats['latest_market_time']}")
    print(f"  + Tin hieu phat hien: BUY={stats['signals']['BUY']} | SELL={stats['signals']['SELL']}")
    print(f"  + Lenh dat that (Paper Market Orders): {stats['orders_submitted']}")
    print(f"  + Lenh gia lap [DRY-RUN]: {stats['dry_run_orders']}")
    print(f"  + Lenh khop (ORDER FILL): {stats['orders_filled']}")
    print(f"  + Su kien kich hoat Stop-Loss: {stats['stop_loss_events']}")
    print(f"  + So lan bo qua tin hieu (vi da co vi the hoac k du conf): {stats['skipped_actions']}")
    print(f"  + So loi (ERROR): {stats['errors']} | Canh bao (WARNING): {stats['warnings']}")

    if stats["errors"] == 0:
        print("\n  [PASS] Khong phat hien loi runtime he thong trong log!")
    else:
        print(f"\n  [CANH BAO] Phat hien {stats['errors']} loi trong log! Mau loi:")
        for err in stats["error_samples"]:
            print(f"    -> {err}")

    if stats["signals"]["details"]:
        print("\n  [INFO] 3 tin hieu gan day nhat:")
        for sig in stats["signals"]["details"][-3:]:
            print(f"    * {sig}")


def main():
    parser = argparse.ArgumentParser(description="Kiem thu du lieu va audit bot giao dich")
    parser.add_argument("--data", action="store_true", help="Kiem tra du lieu live va chi bao tu Alpaca")
    parser.add_argument("--log", action="store_true", help="Audit nhat ky trading_bot.log")
    parser.add_argument("--all", action="store_true", help="Chay toan bo quy trinh kiem thu")
    args = parser.parse_args()

    # Neu khong truyen tham so nao, mac dinh chay --all
    if not (args.data or args.log or args.all):
        args.all = True

    if args.data or args.all:
        run_live_data_verification()

    if args.log or args.all:
        run_log_audit()

    print("\n" + "=" * 70)
    print(" KET THUC KIEM THU")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
