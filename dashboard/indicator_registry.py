"""Metadata registry for price overlays and future separate-pane indicators.

Only registered indicators with a concrete implementation can be computed.
The `pane` field prevents mixing oscillators with the price axis when
additional charts and controls are introduced in later releases.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import pandas as pd

from dashboard.indicators import sma, ema, bollinger_bands


@dataclass(frozen=True)
class IndicatorDefinition:
    code: str
    title: str
    pane: Literal['price', 'oscillator']
    compute: Callable[..., pd.Series | pd.DataFrame]


INDICATORS: dict[str, IndicatorDefinition] = {
    'sma': IndicatorDefinition('sma', 'Simple Moving Average', 'price', sma),
    'ema': IndicatorDefinition('ema', 'Exponential Moving Average', 'price', ema),
    'bollinger': IndicatorDefinition('bollinger', 'Bande di Bollinger', 'price', bollinger_bands),
}


def register_indicator(definition: IndicatorDefinition) -> None:
    if definition.code in INDICATORS:
        raise ValueError('Indicatore gia registrato: ' + definition.code)
    INDICATORS[definition.code] = definition


def indicator(code: str) -> IndicatorDefinition:
    if code not in INDICATORS:
        raise KeyError('Indicatore non implementato: ' + code)
    return INDICATORS[code]
