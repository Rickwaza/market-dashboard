import math

import numpy as np
import pandas as pd
import pytest

from dashboard.indicators import (
    bollinger_bands, ema, historical_volatility, sma, validate_period,
)


def test_sma_has_exact_warmup():
    values = pd.Series([1., 2., 3., 4., 5., 6., 7.])
    result = sma(values, 5)
    assert result.iloc[:4].isna().all()
    assert result.iloc[4] == 3.0
    assert result.iloc[6] == 5.0


def test_ema_uses_full_window_sma_seed():
    values = pd.Series([1., 2., 3., 4., 5., 6., 7.])
    result = ema(values, 5)
    assert result.iloc[:4].isna().all()
    assert result.iloc[4] == 3.0
    assert result.iloc[5] == pytest.approx(4.0)
    assert result.iloc[6] == pytest.approx(5.0)


def test_ema_restarts_after_missing_price():
    values = pd.Series([1., 2., 3., 4., 5., np.nan, 6., 7., 8., 9., 10.])
    result = ema(values, 5)
    assert result.iloc[5:10].isna().all()
    assert result.iloc[10] == pytest.approx(8.0)


def test_bollinger_center_and_population_std():
    values = pd.Series([1., 2., 3., 4., 5.])
    bands = bollinger_bands(values, period=5, multiplier=2.0)
    sd = math.sqrt(2.0)
    assert bands.iloc[4]['middle'] == pytest.approx(3.0)
    assert bands.iloc[4]['upper'] == pytest.approx(3.0 + 2 * sd)
    assert bands.iloc[4]['lower'] == pytest.approx(3.0 - 2 * sd)


def test_historical_volatility_constant_log_returns_is_zero():
    price = pd.Series(100. * np.exp(0.01 * np.arange(80)))
    result = historical_volatility(price, 20, 252)
    assert result.iloc[:20].isna().all()
    assert result.iloc[-1] == pytest.approx(0., abs=1e-10)


def test_historical_volatility_matches_manual_sample_sd():
    returns = np.array([0.02, -.01, .03, -.02] * 20)
    price = pd.Series(100. * np.exp(np.r_[0., returns].cumsum()))
    result = historical_volatility(price, 20, 252)
    expected = float(np.std(returns[:20], ddof=1) * np.sqrt(252) * 100)
    assert result.iloc[20] == pytest.approx(expected)
    assert result.iloc[19] != result.iloc[19]  # still in warm-up


def test_period_validation_rejects_invalid():
    for invalid in (0, 4, 201, 2.0, True, '20'):
        with pytest.raises(ValueError):
            validate_period(invalid)
    with pytest.raises(ValueError):
        bollinger_bands(pd.Series([1., 2.]), 20, 0.)
    with pytest.raises(ValueError):
        historical_volatility(pd.Series([1., 2.]), 40)


def test_short_series_not_populated():
    x = pd.Series([10., 11., 12.])
    assert sma(x, 20).isna().all()
    assert ema(x, 20).isna().all()
    assert bollinger_bands(x, 20).isna().all().all()
    assert historical_volatility(x, 20).isna().all()
