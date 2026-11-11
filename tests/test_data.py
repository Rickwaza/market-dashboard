import numpy as np
import pandas as pd
import pytest

from dashboard.data import MarketDataError, normalize_ohlcv


def test_valid_dataframe_sorted_and_deduplicated():
    idx = pd.to_datetime(['2025-03-03', '2025-03-01', '2025-03-03'])
    raw = pd.DataFrame({'Open':[10.,12.,11.], 'High':[12.,14.,13.],
        'Low':[9.,11.,10.], 'Close':[11.,13.,12.], 'Volume':[1,2,3]}, index=idx)
    cleaned = normalize_ohlcv(raw)
    assert len(cleaned) == 2
    assert cleaned.index.is_monotonic_increasing
    assert cleaned.iloc[-1]['Close'] == 12.


def test_missing_volume_is_not_faked_as_zero():
    df = pd.DataFrame({'Open':[10.], 'High':[11.], 'Low':[9.], 'Close':[10.5]},
                      index=pd.to_datetime(['2025-01-01']))
    actual = normalize_ohlcv(df)
    assert actual['Volume'].isna().all()


def test_bad_ohlc_row_dropped():
    idx = pd.date_range('2025-01-01', periods=3)
    df = pd.DataFrame({'Open':[10.,10.,10.], 'High':[11.,9.,11.],
        'Low':[9.,8.,9.], 'Close':[10.,10.,np.nan], 'Volume':[20,-1,20]}, index=idx)
    actual = normalize_ohlcv(df)
    assert len(actual) == 1


def test_missing_columns_raises():
    with pytest.raises(MarketDataError, match='Colonne obbligatorie'):
        normalize_ohlcv(pd.DataFrame({'Close':[10.]}, index=pd.date_range('2025-01-01', periods=1)))


def test_empty_data_raises():
    with pytest.raises(MarketDataError):
        normalize_ohlcv(pd.DataFrame())


def test_yfinance_multiindex_support(prices):
    df = prices.head(4).copy()
    df.columns = pd.MultiIndex.from_product([['SPY'], df.columns])
    actual = normalize_ohlcv(df)
    assert list(actual.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
    assert len(actual) == 4


def test_timezone_preserves_exchange_date(prices):
    df = prices.head(2).copy()
    df.index = df.index.tz_localize('America/New_York')
    normal = normalize_ohlcv(df)
    assert normal.index[0].date() == df.index[0].date()
    assert normal.index.tz is None
