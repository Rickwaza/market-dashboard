"""Pure, provider-independent indicator implementations."""
from __future__ import annotations

from math import sqrt

import numpy as np
import pandas as pd


def validate_period(period: int, minimum: int = 5, maximum: int = 200) -> int:
    if isinstance(period, bool) or not isinstance(period, (int, np.integer)):
        raise ValueError('Il periodo deve essere un intero.')
    if not minimum <= period <= maximum:
        raise ValueError(f'Periodo fuori intervallo [{minimum}, {maximum}]: {period}')
    return int(period)


def _close(close: pd.Series) -> pd.Series:
    return pd.to_numeric(close, errors='coerce').astype(float)


def sma(close: pd.Series, period: int) -> pd.Series:
    period = validate_period(period)
    return _close(close).rolling(window=period, min_periods=period).mean().rename(f'SMA {period}')


def ema(close: pd.Series, period: int) -> pd.Series:
    period = validate_period(period)
    s = _close(close)
    # First valid EMA is the SMA seed of the first full window, not a
    # misleading short-history exponentially weighted estimate.
    result = pd.Series(np.nan, index=s.index, dtype=float, name=f'EMA {period}')
    # Missing prices restart the warm-up rather than connecting disjoint runs.
    run = s.notna()
    group = run.ne(run.shift(fill_value=False)).cumsum()
    alpha = 2.0 / (period + 1.0)
    for _, series in s[run].groupby(group[run]):
        if len(series) < period:
            continue
        seed = float(series.iloc[:period].mean())
        result.loc[series.index[period - 1]] = seed
        previous = seed
        for idx, value in series.iloc[period:].items():
            previous = alpha * float(value) + (1.0 - alpha) * previous
            result.loc[idx] = previous
    return result


def bollinger_bands(close: pd.Series, period: int = 20, multiplier: float = 2.0) -> pd.DataFrame:
    period = validate_period(period)
    if not np.isfinite(multiplier) or not 0.1 <= multiplier <= 5.0:
        raise ValueError('Moltiplicatore Bollinger fuori intervallo [0.1, 5.0].')
    center = sma(close, period)
    std = _close(close).rolling(window=period, min_periods=period).std(ddof=0)
    return pd.DataFrame({
        'lower': center - multiplier * std,
        'middle': center,
        'upper': center + multiplier * std,
    }, index=close.index)


def historical_volatility(close: pd.Series, period: int = 20, sessions_per_year: int = 252) -> pd.Series:
    if period not in (20, 30, 60):
        raise ValueError('Finestra volatilita: solo 20, 30 o 60 sedute.')
    if not isinstance(sessions_per_year, int) or not 200 <= sessions_per_year <= 366:
        raise ValueError('Sedute annue fuori intervallo [200, 366].')
    prices = _close(close).where(lambda s: s > 0)
    returns = np.log(prices / prices.shift(1))
    returns = returns.replace([np.inf, -np.inf], np.nan)
    return (returns.rolling(period, min_periods=period).std(ddof=1) * sqrt(sessions_per_year) * 100).rename('HV')
