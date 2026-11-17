import logging
from datetime import datetime, timedelta

import pandas as pd
from alpaca_trade_api.rest import TimeFrame

COLUMNS = ["open", "high", "low", "close", "volume"]


class DataManager:
    """Lay va chuan hoa du lieu nen crypto tu Alpaca."""

    def __init__(self, api):
        self.api = api
        self.logger = logging.getLogger("TradingBot.data")

    def get_historical_data(self, symbol: str, days: int = 100) -> pd.DataFrame:
        end = datetime.now()
        start = end - timedelta(days=days)
        try:
            bars = self.api.get_crypto_bars(
                symbol, TimeFrame.Day,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                loc="us",
            ).df
        except Exception as e:
            self.logger.error("Loi lay du lieu %s: %s", symbol, e)
            return pd.DataFrame(columns=COLUMNS)

        if bars is None or bars.empty:
            self.logger.warning("Khong co du lieu cho %s", symbol)
            return pd.DataFrame(columns=COLUMNS)

        bars = bars.rename(columns=str.lower)
        missing = [c for c in COLUMNS if c not in bars.columns]
        if missing:
            self.logger.warning("%s thieu cot %s", symbol, missing)
            return pd.DataFrame(columns=COLUMNS)
        return bars[COLUMNS].dropna().sort_index()


class TradingViewDataManager(DataManager):
    """KHUNG theo muc 'Integrating TradingView Data' trong bai (chua cai dat).

    Can tai khoan TradingView va thu vien tvDatafeed (khong co trong requirements.txt).
    """

    def __init__(self, tv_username: str, tv_password: str):
        super().__init__(api=None)
        self.tv_username, self.tv_password = tv_username, tv_password
        # TODO: from tvDatafeed import TvDatafeed, Interval
        #       self.tv_client = TvDatafeed(tv_username, tv_password)

    def get_historical_data(self, symbol: str, days: int = 100) -> pd.DataFrame:
        # TODO: return self.tv_client.get_hist(symbol, exchange="NASDAQ", interval=Interval.in_daily, n_bars=days)
        #       roi chuan hoa ten cot ve open/high/low/close/volume
        raise NotImplementedError("Chua cai dat TradingView")
