import json

import pytest

from dashboard.config import DEFAULT_CHART, beginning_of_window, display_window
from dashboard.settings import default_preferences, export_preferences, validate_chart, validate_preferences
from dashboard.symbols import is_valid_isin, resolve_isin, clean_symbol


def test_isin_checksum():
    assert is_valid_isin('US0378331005')
    assert is_valid_isin('IE00B4L5Y983')
    assert not is_valid_isin('US0378331006')
    assert not is_valid_isin('AAPL')


def test_isin_candidates_mark_unknown_unverified():
    search = lambda code: [
        {'symbol':'AAPL','shortname':'Apple','exchange':'NMS'},
        {'symbol':'MSFT','shortname':'Microsoft','exchange':'NMS'},
    ]
    result = resolve_isin('US0378331005', search, lambda symbol: 'US0378331005' if symbol == 'AAPL' else None)
    assert len(result) == 2
    assert result[0].verified is True
    assert result[1].verified is False


def test_isin_search_without_validation_never_claims_match():
    result = resolve_isin('US0378331005', lambda _: [{'symbol':'AAPL'}])
    assert result[0].verified is False


def test_ticker_validation():
    assert clean_symbol(' brk-b ') == 'BRK-B'
    for bad in ('', 'https://a', 'ABC;rm -rf /', 'a b'):
        with pytest.raises(ValueError):
            clean_symbol(bad)


def test_preferences_roundtrip():
    prefs = default_preferences()
    prefs['charts']['AAPL']['sma'] = [10, 20, 50]
    prefs['metadata']['AAPL'] = {'isin': 'US0378331005', 'name':'Apple', 'exchange':'NMS', 'verified':True}
    loaded = validate_preferences(json.loads(export_preferences(prefs)))
    assert loaded == prefs


def test_preference_clamping():
    raw = {
        'instruments': ['AAPL','AAPL','MSFT','SPY','AMZN','GOOG','IBM','TSLA'],
        'columns': 500, 'global_period':'20Y',
        'charts': {'AAPL': {'sma':[4,20,300,'10',20], 'ema': [21], 'bb_std': 20}},
    }
    cfg = validate_preferences(raw)
    assert len(cfg['instruments']) == 6
    assert cfg['columns'] == 2
    assert cfg['global_period'] == '1Y'
    assert cfg['charts']['AAPL']['sma'] == [20]
    assert cfg['charts']['AAPL']['bb_std'] == 2.


def test_time_window_reject_invalid_and_limit(prices):
    assert len(display_window(prices, '1M')) <= len(prices)
    with pytest.raises(ValueError):
        beginning_of_window('10Y')


def test_five_year_window_is_capped():
    import pandas as pd
    dates = pd.bdate_range(end=pd.Timestamp.now(tz='UTC').tz_localize(None).normalize(), periods=1800)
    data = pd.DataFrame({'Close':range(len(dates))}, index=dates)
    visible = display_window(data, '5Y')
    assert len(visible) < len(data)
    assert visible.index.min() >= beginning_of_window('5Y')
