import pandas as pd


def simple_moving_average(prices: pd.Series, length: int) -> pd.Series:
    """TradingView SMA: arithmetic mean of the latest `length` source values."""
    if length < 1:
        raise ValueError("length phai >= 1")
    return prices.rolling(window=length, min_periods=length).mean()


def wilder_rsi(prices: pd.Series, length: int = 14) -> pd.Series:
    """TradingView ta.rsi-style RSI using Wilder's RMA smoothing."""
    if length < 1:
        raise ValueError("length phai >= 1")

    changes = prices.astype(float).diff()
    gains = changes.clip(lower=0)
    losses = -changes.clip(upper=0)
    avg_gain = pd.Series(float("nan"), index=prices.index, dtype=float)
    avg_loss = pd.Series(float("nan"), index=prices.index, dtype=float)

    # ta.rma seeds its recursion with the SMA of the first `length` changes.
    if len(prices) <= length:
        return avg_gain
    avg_gain.iloc[length] = gains.iloc[1:length + 1].mean()
    avg_loss.iloc[length] = losses.iloc[1:length + 1].mean()
    for i in range(length + 1, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (length - 1) + gains.iloc[i]) / length
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (length - 1) + losses.iloc[i]) / length

    relative_strength = avg_gain / avg_loss
    return 100 - (100 / (1 + relative_strength))


def add_macd_indicator(data: pd.DataFrame) -> pd.DataFrame:
    """MACD nhu muc 'Adding Technical Indicators' trong bai."""
    exp1 = data["close"].ewm(span=12).mean()
    exp2 = data["close"].ewm(span=26).mean()
    data["MACD"] = exp1 - exp2
    data["MACD_signal"] = data["MACD"].ewm(span=9).mean()
    return data
