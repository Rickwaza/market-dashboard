from types import SimpleNamespace
import sys
import pandas as pd

from dashboard.charts import build_price_figure, build_volatility_figure
from dashboard.indicators import historical_volatility
from dashboard.provider import YahooFinanceProvider
from dashboard.settings import validate_chart


def test_price_contains_candles_volume_and_all_overlays(prices):
    cfg = validate_chart({'sma':[20,50,200], 'ema':[21], 'bollinger':True})
    figure = build_price_figure(prices, 'SPY', cfg, '5Y')
    assert len(figure.data) == 9  # candles + SMA*3 + EMA + BB*3 + volume
    names = [trace.name for trace in figure.data]
    for name in ('SMA 20','SMA 50','SMA 200','EMA 21','BB inferiore','BB superiore','Volume'):
        assert name in names
    assert len([trace for trace in figure.data if trace.type == 'candlestick']) == 1
    assert 'Volume:' in figure.data[0].text[0]


def test_indicators_remain_independent(prices):
    a = validate_chart({'sma':[20], 'ema':[]})
    b = validate_chart({'sma':[50, 200], 'ema':[21], 'bollinger':True})
    af = build_price_figure(prices, 'AAPL', a, '1Y')
    bf = build_price_figure(prices, 'MSFT', b, '1Y')
    assert 'SMA 200' not in [t.name for t in af.data]
    assert 'SMA 200' in [t.name for t in bf.data]


def test_vix_separate_subplot_with_hv(prices):
    hv = historical_volatility(prices['Close'], 30)
    fig = build_volatility_figure(prices, {'AAPL':hv}, '3Y', 30, True)
    assert [t.name for t in fig.data] == ['VIX','HV AAPL']
    assert len(fig.layout.shapes) == 4
    assert fig.data[0].yaxis != fig.data[1].yaxis


def test_volatility_can_render_without_vix(prices):
    hv = historical_volatility(prices['Close'], 20)
    fig = build_volatility_figure(None, {'AAPL':hv}, '1Y', 20, False)
    assert len(fig.data) == 1


def test_provider_with_injected_yfinance(monkeypatch, prices):
    class StubTicker:
        isin = 'US0378331005'
        def history(self, **kwargs):
            assert kwargs['auto_adjust'] is True
            assert kwargs['interval'] == '1d'
            assert 'start' in kwargs and 'end' in kwargs
            return prices.head(10)
    fake = SimpleNamespace(Ticker=lambda t: StubTicker(),
        Search=lambda q, **kw: SimpleNamespace(quotes=[{'symbol':'AAPL'}]))
    monkeypatch.setitem(sys.modules, 'yfinance', fake)
    p = YahooFinanceProvider()
    assert len(p.fetch('AAPL').frame) == 10
    assert p.search('US0378331005')[0]['symbol'] == 'AAPL'
    assert p.lookup_isin('AAPL') == 'US0378331005'


def test_unknown_indicator_cannot_be_computed():
    import pytest
    from dashboard.indicator_registry import IndicatorDefinition, indicator, register_indicator
    with pytest.raises(KeyError):
        indicator('rsi')
    custom = IndicatorDefinition('example_osc', 'Esempio', 'oscillator', lambda series: series)
    register_indicator(custom)
    assert indicator('example_osc').pane == 'oscillator'
    with pytest.raises(ValueError):
        register_indicator(custom)


def test_provider_error_is_wrapped(monkeypatch):
    import pytest
    from dashboard.data import MarketDataError
    class BrokenTicker:
        def history(self, **kwargs):
            raise ConnectionError('simulazione offline')
    monkeypatch.setitem(sys.modules, 'yfinance', SimpleNamespace(Ticker=lambda _: BrokenTicker()))
    with pytest.raises(MarketDataError, match='simulazione offline'):
        YahooFinanceProvider().fetch('FAKE')


def test_price_chart_with_missing_volume(prices):
    values = prices.copy()
    values['Volume'] = float('nan')
    fig = build_price_figure(values, 'NOVOL', validate_chart({}), '1Y')
    assert not any(trace.type == 'bar' for trace in fig.data)
    assert 'Volume non disponibile' in [a.text for a in fig.layout.annotations]
