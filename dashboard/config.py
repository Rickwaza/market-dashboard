"""Application-wide constants and interval helpers."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_FILE = ROOT / 'config' / 'defaults.json'
CACHE_TTL_SECONDS = max(60, int(os.getenv('MARKET_CACHE_TTL', '900')))
MAX_INSTRUMENTS = 6
TIME_WINDOWS = {
    '1M': pd.DateOffset(months=1),
    '3M': pd.DateOffset(months=3),
    '6M': pd.DateOffset(months=6),
    '1Y': pd.DateOffset(years=1),
    '2Y': pd.DateOffset(years=2),
    '3Y': pd.DateOffset(years=3),
    '5Y': pd.DateOffset(years=5),
}
VIX_WINDOWS = tuple(k for k in TIME_WINDOWS if k != '5Y')
CHART_COLORS = ('#38bdf8', '#f59e0b', '#a78bfa', '#2dd4bf', '#f472b6', '#facc15', '#fb923c', '#c084fc')
DEFAULT_CHART = {
    'period': '1Y', 'sma': [20, 50], 'ema': [21],
    'bollinger': False, 'bb_period': 20, 'bb_std': 2.0, 'bb_fill': True,
}


def beginning_of_window(period: str, end: pd.Timestamp | None = None) -> pd.Timestamp:
    if period not in TIME_WINDOWS:
        raise ValueError(f'Intervallo non supportato: {period}')
    if end is None:
        end = pd.Timestamp.now(tz='UTC').tz_localize(None).normalize()
    return end - TIME_WINDOWS[period]


def display_window(data: pd.DataFrame, period: str, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Restrict visible history without shortening the indicator warm-up series."""
    if data.empty:
        return data.copy()
    return data.loc[data.index >= beginning_of_window(period, end)].copy()
