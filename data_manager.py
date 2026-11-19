"""data_manager.py: Lay va chuan hoa du lieu nen (Stocks qua IEX & Crypto 24/7) tu Alpaca."""
import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca_trade_api.rest import TimeFrame

COLUMNS = ["open", "high", "low", "close", "volume"]


class DataManager:
    """Lay va chuan hoa du lieu lich su tu Alpaca API."""

    def __init__(self, api, feed: str = "iex"):
        self.api = api
        self.feed = feed
        self.logger = logging.getLogger("TradingBot.data")

    def get_historical_data(self, symbol: str, days: int = 5) -> pd.DataFrame:
        """Lay du lieu phuc vu chu ky giao dich (mac dinh nen 1 phut)."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        is_crypto = "/" in symbol

        try:
            if is_crypto:
                bars = self.api.get_crypto_bars(
                    symbol, TimeFrame.Minute,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    limit=10000,
                    loc="us",
                ).df
            else:
                bars = self.api.get_bars(
                    symbol, TimeFrame.Minute,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    adjustment="raw",
                    feed=self.feed,
                ).df
        except Exception as e:
            self.logger.error("Loi lay du lieu lich su cho %s: %s", symbol, e)
            return pd.DataFrame(columns=COLUMNS)

        return self._clean_bars(bars, symbol)

    def get_daily_bars(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """Lay nến ngay (Daily) phuc vu Stock Screening (ADV, Volatility, Correlation)."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        is_crypto = "/" in symbol

        try:
            if is_crypto:
                bars = self.api.get_crypto_bars(
                    symbol, TimeFrame.Day,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    loc="us",
                ).df
            else:
                bars = self.api.get_bars(
                    symbol, TimeFrame.Day,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    adjustment="raw",
                    feed=self.feed,
                ).df
        except Exception as e:
            self.logger.error("Loi lay nến ngay cho %s: %s", symbol, e)
            return pd.DataFrame(columns=COLUMNS)

        return self._clean_bars(bars, symbol)

    def _clean_bars(self, bars: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Chuan hoa ten cot va loc bo gia tri loi."""
        if bars is None or bars.empty:
            self.logger.warning("Khong co du lieu tra ve cho %s", symbol)
            return pd.DataFrame(columns=COLUMNS)

        bars = bars.rename(columns=str.lower)
        missing = [c for c in COLUMNS if c not in bars.columns]
        if missing:
            self.logger.warning("%s thieu cot bat buoc: %s", symbol, missing)
            return pd.DataFrame(columns=COLUMNS)

        return bars[COLUMNS].dropna().sort_index()


class TradingViewDataManager(DataManager):
    """KHUNG theo muc 'Integrating TradingView Data' trong bai (chua cai dat)."""

    def __init__(self, tv_username: str, tv_password: str):
        super().__init__(api=None)
        self.tv_username, self.tv_password = tv_username, tv_password

    def get_historical_data(self, symbol: str, days: int = 100) -> pd.DataFrame:
        raise NotImplementedError("Chua cai dat TradingView")
