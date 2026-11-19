"""stock_screener.py: Historical Data-based Stock Screening Module.

Sang loc co phieu dua tren 4 tieu chi du lieu lich su tu Alpaca:
1. Data Completeness: Tinh day du, hop le va khong di thuong cua nen OHLCV.
2. Liquidity: Average Dollar Volume (ADV = Mean(Close * Volume)).
3. Volatility: Do lech chuan loi suat ngay thuong nien hoa (Annualized Volatility = std(R_t) * sqrt(252)).
4. Correlation: Ma tran tuong quan Pearson va thuat toan Greedy Pruning tranh trung lap danh muc.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import TradingConfig
from data_manager import DataManager

REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


@dataclass
class StockMetrics:
    """Chi so tai chinh va trang thai sang loc cua tung ma."""
    symbol: str
    total_bars: int = 0
    data_valid: bool = False
    data_issues: List[str] = field(default_factory=list)
    adv: float = 0.0
    adv_passed: bool = False
    volatility_daily: float = 0.0
    volatility_annual: float = 0.0
    volatility_passed: bool = False
    overall_passed: bool = False
    status: str = "FAILED_DATA"  # QUALIFIED | FAILED_DATA | FAILED_LIQUIDITY | FAILED_VOLATILITY | PRUNED_CORRELATION | SELECTED
    reason: str = ""


@dataclass
class ScreeningResult:
    """Ket qua tong hop cua toan bo quy trinh sang loc."""
    universe: List[str]
    valid_data_symbols: List[str]
    metrics: Dict[str, StockMetrics]
    qualified_symbols: List[str]  # Vuot qua ca Data, ADV va Volatility
    correlation_matrix: pd.DataFrame
    selected_symbols: List[str]   # Danh sach cuoi cung sau khi loc tuong quan de dua vao Bot
    pruned_symbols: List[str]     # Cac ma bi loai do tuong quan qua cao
    summary_df: pd.DataFrame      # Bang tong hop phuc vu Dashboard va Bao cao


class DataQualityValidator:
    """Kiem tra tinh day du, tinh toan ven va phat hien di thuong trong nen OHLCV."""

    @staticmethod
    def validate(df: pd.DataFrame, symbol: str, min_bars: int = 30) -> Tuple[bool, List[str]]:
        issues: List[str] = []

        if df is None or df.empty:
            return False, [f"[{symbol}] Du lieu rong (0 nen)"]

        # 1. Kiem tra so luong nen toi thieu
        if len(df) < min_bars:
            issues.append(f"[{symbol}] So nen ({len(df)}) khong du nguong toi thieu ({min_bars})")

        # 2. Kiem tra cac cot bat buoc
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            issues.append(f"[{symbol}] Thieu cac cot bat buoc: {missing}")
            return False, issues

        # 3. Kiem tra gia tri NaN / Null
        nulls = df[REQUIRED_COLUMNS].isna().sum()
        for col, count in nulls.items():
            if count > 0:
                issues.append(f"[{symbol}] Cot {col} chua {count} gia tri NaN/Null")

        # 4. Kiem tra trung lap timestamp
        if df.index.duplicated().sum() > 0:
            dup_count = int(df.index.duplicated().sum())
            issues.append(f"[{symbol}] Phat hien {dup_count} nến bi trung lap timestamp")

        # 5. Kiem tra logic hinh hoc gia (High >= Low, High >= Open/Close, Low <= Open/Close)
        invalid_hl = (df["high"] < df["low"]).sum()
        if invalid_hl > 0:
            issues.append(f"[{symbol}] Co {invalid_hl} nến vi pham High < Low")

        invalid_ho = (df["high"] < df["open"]).sum()
        invalid_hc = (df["high"] < df["close"]).sum()
        if invalid_ho > 0 or invalid_hc > 0:
            issues.append(f"[{symbol}] Co nến vi pham High < Open hoac High < Close")

        invalid_lo = (df["low"] > df["open"]).sum()
        invalid_lc = (df["low"] > df["close"]).sum()
        if invalid_lo > 0 or invalid_lc > 0:
            issues.append(f"[{symbol}] Co nến vi pham Low > Open hoac Low > Close")

        # 6. Kiem tra gia am hoac bang 0
        for col in ["open", "high", "low", "close"]:
            non_pos = (df[col] <= 0).sum()
            if non_pos > 0:
                issues.append(f"[{symbol}] Co {non_pos} nến co gia {col} <= 0")

        # 7. Kiem tra Volume am
        neg_vol = (df["volume"] < 0).sum()
        if neg_vol > 0:
            issues.append(f"[{symbol}] Co {neg_vol} nến co Volume am")

        is_valid = len(issues) == 0
        return is_valid, issues


class StockScreener:
    """Engine sang loc danh muc co phieu dua tren du lieu lich su OHLCV tu Alpaca."""

    def __init__(self, data_manager: DataManager, config: TradingConfig):
        self.dm = data_manager
        self.config = config
        self.logger = logging.getLogger("TradingBot.screener")
        self.validator = DataQualityValidator()

    @staticmethod
    def calculate_liquidity(df: pd.DataFrame) -> float:
        """Tinh Average Dollar Volume (ADV = Mean(Close * Volume))."""
        if df.empty or "close" not in df.columns or "volume" not in df.columns:
            return 0.0
        dollar_vol = df["close"] * df["volume"]
        return round(float(dollar_vol.mean()), 2)

    @staticmethod
    def calculate_volatility(df: pd.DataFrame) -> Tuple[float, float]:
        """Tinh do lech chuan loi suat ngay va thuong nien hoa (std * sqrt(252))."""
        if df.empty or len(df) < 5 or "close" not in df.columns:
            return 0.0, 0.0

        # Lợi suất ngày liên tiếp R_t = (Close_t - Close_{t-1}) / Close_{t-1}
        returns = df["close"].pct_change().dropna()
        if len(returns) == 0:
            return 0.0, 0.0

        daily_std = float(returns.std(ddof=1))
        # Quy tắc căn bậc hai của thời gian: Annualized Volatility = daily_std * sqrt(252)
        annual_std = daily_std * math.sqrt(252)

        return round(daily_std, 6), round(annual_std, 4)

    @staticmethod
    def calculate_correlation_matrix(dfs_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Xay dung ma tran tuong quan Pearson giua cac chuoi loi suat ngay."""
        if not dfs_dict or len(dfs_dict) < 2:
            symbols = list(dfs_dict.keys()) if dfs_dict else []
            return pd.DataFrame(index=symbols, columns=symbols)

        # Gom gia Close vao 1 DataFrame theo DatetimeIndex chung
        close_dict = {}
        for sym, df in dfs_dict.items():
            if not df.empty and "close" in df.columns:
                close_dict[sym] = df["close"]

        if not close_dict:
            return pd.DataFrame()

        prices_df = pd.DataFrame(close_dict).sort_index().ffill().dropna()
        if len(prices_df) < 5:
            # Khong du nến dong thoi de tinh correlation dang tin cay
            return pd.DataFrame(1.0, index=close_dict.keys(), columns=close_dict.keys())

        returns_df = prices_df.pct_change().dropna()
        corr_matrix = returns_df.corr(method="pearson")
        return corr_matrix.round(4)

    def prune_correlated_assets(
        self,
        qualified_symbols: List[str],
        metrics_dict: Dict[str, StockMetrics],
        corr_matrix: pd.DataFrame,
        max_corr: float,
        target_n: int,
    ) -> Tuple[List[str], List[str]]:
        """Thuat toan Greedy Pruning:

        1. Sap xep cac ma dat tieu chuan ADV & Volatility theo ADV giam dan (uu tien thanh khoan tot nhat).
        2. Chon ma dau tien vao danh sach Selected.
        3. Duyet tung ma tiep theo: neu tuong quan voi bat ky ma nao da co trong Selected > max_corr
           thi loai bo (pruned) de tranh trung lap rui ro nganh/he thong.
        4. Dung lai khi da chon du target_n ma.
        """
        if not qualified_symbols:
            return [], []

        # Sap xep theo ADV giam dan
        sorted_symbols = sorted(
            qualified_symbols,
            key=lambda s: metrics_dict[s].adv if s in metrics_dict else 0,
            reverse=True,
        )

        selected: List[str] = []
        pruned: List[str] = []

        for symbol in sorted_symbols:
            if len(selected) >= target_n:
                pruned.append(symbol)
                metrics_dict[symbol].status = "PRUNED_LIMIT"
                metrics_dict[symbol].reason = f"Da du so luong {target_n} ma toi uu"
                continue

            # Kiem tra tuong quan voi cac ma da duoc chon
            is_correlated = False
            correlated_with = ""
            corr_val = 0.0

            for sel in selected:
                if (
                    not corr_matrix.empty
                    and symbol in corr_matrix.index
                    and sel in corr_matrix.columns
                ):
                    val = corr_matrix.loc[symbol, sel]
                    if not pd.isna(val) and val > max_corr:
                        is_correlated = True
                        correlated_with = sel
                        corr_val = float(val)
                        break

            if is_correlated:
                pruned.append(symbol)
                metrics_dict[symbol].status = "PRUNED_CORRELATION"
                metrics_dict[symbol].reason = (
                    f"Tuong quan cao voi {correlated_with} (r = {corr_val:.2f} > {max_corr})"
                )
                self.logger.info(
                    "LOAI %s: Tuong quan cao voi %s (r = %.2f > %.2f)",
                    symbol, correlated_with, corr_val, max_corr,
                )
            else:
                selected.append(symbol)
                metrics_dict[symbol].status = "SELECTED"
                metrics_dict[symbol].reason = "Dat toan bo tieu chi va toi uu tuong quan"
                self.logger.info("CHON %s: ADV=$%.0f, Vol=%.1f%%",
                                 symbol, metrics_dict[symbol].adv,
                                 metrics_dict[symbol].volatility_annual * 100)

        return selected, pruned

    def run_screening(self, universe: Optional[List[str]] = None) -> ScreeningResult:
        """Thuc thi toan bo quy trinh sang loc co phieu."""
        symbols = universe or self.config.screening_universe
        lookback = self.config.screening_lookback_days
        min_bars = int(lookback * 0.7)  # Yeu cau it nhat 70% so ngay giao dich thuc te

        self.logger.info("=== BAT DAU SANG LOC CO PHIEU (Universe: %s) ===", symbols)

        metrics_dict: Dict[str, StockMetrics] = {}
        valid_dfs: Dict[str, pd.DataFrame] = {}
        qualified_symbols: List[str] = []

        # Buoc 1 & 2 & 3: Kiem tra Data, Tinh ADV va Volatility
        for sym in symbols:
            m = StockMetrics(symbol=sym)
            df = self.dm.get_daily_bars(sym, days=lookback)
            m.total_bars = len(df)

            valid, issues = self.validator.validate(df, sym, min_bars=min_bars)
            m.data_valid = valid
            m.data_issues = issues

            if not valid:
                m.status = "FAILED_DATA"
                m.reason = "; ".join(issues)
                self.logger.warning("Ma %s khong vuot qua kiem tra du lieu: %s", sym, m.reason)
                metrics_dict[sym] = m
                continue

            valid_dfs[sym] = df

            # Tinh ADV
            adv = self.calculate_liquidity(df)
            m.adv = adv
            m.adv_passed = adv >= self.config.min_adv

            # Tinh Volatility
            daily_v, annual_v = self.calculate_volatility(df)
            m.volatility_daily = daily_v
            m.volatility_annual = annual_v
            m.volatility_passed = self.config.min_volatility <= annual_v <= self.config.max_volatility

            # Danh gia tong the buoc loc co ban
            if not m.adv_passed:
                m.status = "FAILED_LIQUIDITY"
                m.reason = f"ADV ${adv:,.0f} < ${self.config.min_adv:,.0f}"
                self.logger.info("Loai %s: %s", sym, m.reason)
            elif not m.volatility_passed:
                m.status = "FAILED_VOLATILITY"
                if annual_v < self.config.min_volatility:
                    m.reason = f"Bien dong qua thap: {annual_v*100:.1f}% < {self.config.min_volatility*100:.1f}%"
                else:
                    m.reason = f"Bien dong qua cao: {annual_v*100:.1f}% > {self.config.max_volatility*100:.1f}%"
                self.logger.info("Loai %s: %s", sym, m.reason)
            else:
                m.overall_passed = True
                m.status = "QUALIFIED"
                m.reason = f"ADV ${adv:,.0f} hop le, Bien dong {annual_v*100:.1f}% hop le"
                qualified_symbols.append(sym)

            metrics_dict[sym] = m

        # Buoc 4: Ma tran tuong quan va Pruning
        corr_matrix = self.calculate_correlation_matrix(valid_dfs)

        selected_symbols, pruned_symbols = self.prune_correlated_assets(
            qualified_symbols=qualified_symbols,
            metrics_dict=metrics_dict,
            corr_matrix=corr_matrix,
            max_corr=self.config.max_correlation,
            target_n=self.config.target_top_n,
        )

        # Tao DataFrame tong hop
        rows = []
        for sym in symbols:
            m = metrics_dict.get(sym, StockMetrics(symbol=sym))
            rows.append({
                "Symbol": sym,
                "Total Bars": m.total_bars,
                "Data Status": "VALID" if m.data_valid else "INVALID",
                "ADV ($)": m.adv,
                "Annual Volatility": f"{m.volatility_annual * 100:.2f}%",
                "Screening Status": m.status,
                "Reason": m.reason,
            })
        summary_df = pd.DataFrame(rows)

        self.logger.info("=== KET THUC SANG LOC: Selected = %s ===", selected_symbols)

        return ScreeningResult(
            universe=symbols,
            valid_data_symbols=list(valid_dfs.keys()),
            metrics=metrics_dict,
            qualified_symbols=qualified_symbols,
            correlation_matrix=corr_matrix,
            selected_symbols=selected_symbols,
            pruned_symbols=pruned_symbols,
            summary_df=summary_df,
        )
