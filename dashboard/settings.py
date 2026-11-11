"""Portable, validated JSON preferences. Never saved to ephemeral cloud disk."""
from __future__ import annotations

import copy
import json
from typing import Any

from dashboard.config import DEFAULTS_FILE, DEFAULT_CHART, MAX_INSTRUMENTS, TIME_WINDOWS, VIX_WINDOWS
from dashboard.symbols import clean_symbol


def default_preferences() -> dict:
    with DEFAULTS_FILE.open(encoding='utf-8') as f:
        return validate_preferences(json.load(f))


def validate_chart(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    cfg = copy.deepcopy(DEFAULT_CHART)
    if raw.get('period') in TIME_WINDOWS:
        cfg['period'] = raw['period']
    for kind in ('sma', 'ema'):
        values = raw.get(kind, cfg[kind])
        if isinstance(values, list):
            cfg[kind] = sorted(set(x for x in values if type(x) is int and 5 <= x <= 200))[:12]
    for key in ('bollinger', 'bb_fill'):
        if type(raw.get(key)) is bool:
            cfg[key] = raw[key]
    if type(raw.get('bb_period')) is int and 5 <= raw['bb_period'] <= 200:
        cfg['bb_period'] = raw['bb_period']
    if type(raw.get('bb_std')) in (float, int) and 0.1 <= raw['bb_std'] <= 5.0:
        cfg['bb_std'] = float(raw['bb_std'])
    return cfg


def validate_preferences(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError('Il file JSON deve contenere un oggetto.')
    instruments = raw.get('instruments', [])
    if not isinstance(instruments, list):
        raise ValueError('La lista degli strumenti deve essere un array.')
    result: list[str] = []
    for ticker in instruments:
        if not isinstance(ticker, str):
            continue
        try:
            symbol = clean_symbol(ticker)
        except ValueError:
            continue
        if symbol not in result:
            result.append(symbol)
        if len(result) == MAX_INSTRUMENTS:
            break
    charts = raw.get('charts') if isinstance(raw.get('charts'), dict) else {}
    meta = raw.get('metadata') if isinstance(raw.get('metadata'), dict) else {}
    metadata = {}
    for ticker in result:
        item = meta.get(ticker)
        if isinstance(item, dict):
            metadata[ticker] = {
                'name': str(item.get('name') or '')[:120],
                'exchange': str(item.get('exchange') or '')[:80],
                'verified': item.get('verified') is True,
            }
            if item.get('verified') is True and isinstance(item.get('isin'), str):
                from dashboard.symbols import is_valid_isin
                if is_valid_isin(item['isin']):
                    metadata[ticker]['isin'] = item['isin'].upper()
    preferences = {
        'version': 1,
        'instruments': result,
        'charts': {ticker: validate_chart(charts.get(ticker, {})) for ticker in result},
        'metadata': metadata,
        'columns': int(raw['columns']) if type(raw.get('columns')) is int and 1 <= raw['columns'] <= 3 else 2,
        'sync_periods': bool(raw.get('sync_periods', True)),
        'global_period': raw.get('global_period') if raw.get('global_period') in TIME_WINDOWS else '1Y',
        'vix_period': raw.get('vix_period') if raw.get('vix_period') in VIX_WINDOWS else '1Y',
        'vix_thresholds': bool(raw.get('vix_thresholds', True)),
        'vol_window': raw.get('vol_window') if raw.get('vol_window') in (20, 30, 60) else 20,
        'sessions_per_year': int(raw['sessions_per_year']) if type(raw.get('sessions_per_year')) is int and 200 <= raw['sessions_per_year'] <= 366 else 252,
    }
    return preferences


def export_preferences(prefs: dict) -> str:
    return json.dumps(validate_preferences(prefs), indent=2, ensure_ascii=False) + '\n'
