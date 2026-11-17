import pandas as pd


def add_macd_indicator(data: pd.DataFrame) -> pd.DataFrame:
    """MACD nhu muc 'Adding Technical Indicators' trong bai."""
    exp1 = data["close"].ewm(span=12).mean()
    exp2 = data["close"].ewm(span=26).mean()
    data["MACD"] = exp1 - exp2
    data["MACD_signal"] = data["MACD"].ewm(span=9).mean()
    return data
