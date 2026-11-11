"""OHLCV validation. Rows with invalid price geometry are rejected."""
from __future__ import annotations

import numpy as np
import pandas as pd

PRICE_COLS = ('Open', 'High', 'Low', 'Close')
DATA_COLS = (*PRICE_COLS, 'Volume')


class MarketDataError(ValueError):
    """Unusable data returned by the market provider."""


def normalize_ohlcv(raw: pd.DataFrame | None) -> pd.DataFrame:
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        raise MarketDataError('Nessuna serie storica disponibile.')
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance may use (field, ticker) or (ticker, field).
        mapped = []
        for col in df.columns:
            names = [str(part) for part in col]
            matched = next((x for x in names if x.lower() in {'open', 'high', 'low', 'close', 'volume'}), None)
            mapped.append(matched or str(col[0]))
        df.columns = mapped
    renamed = {str(c): str(c).strip().title() for c in df.columns}
    df = df.rename(columns=renamed)
    if df.columns.duplicated().any():
        raise MarketDataError('Colonne OHLCV duplicate o riferite a piu strumenti.')
    missing = [c for c in PRICE_COLS if c not in df.columns]
    if missing:
        raise MarketDataError('Colonne obbligatorie mancanti: ' + ', '.join(missing))
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index, errors='raise')
        except (ValueError, TypeError) as exc:
            raise MarketDataError('Indice temporale non valido.') from exc
    if df.index.tz is not None:
        # Preserve the provider's exchange-local trading date.
        df.index = df.index.tz_localize(None)
    df = df[~df.index.isna()].sort_index()
    df = df[~df.index.duplicated(keep='last')]
    if 'Volume' not in df.columns:
        df['Volume'] = np.nan
    for col in DATA_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    good = df[list(PRICE_COLS)].notna().all(axis=1)
    for col in PRICE_COLS:
        good &= np.isfinite(df[col]) & (df[col] > 0)
    good &= df['High'] + 1e-8 >= df[['Open', 'Close', 'Low']].max(axis=1)
    good &= df['Low'] - 1e-8 <= df[['Open', 'Close', 'High']].min(axis=1)
    df = df.loc[good, list(DATA_COLS)].copy()
    df['Volume'] = df['Volume'].where(df['Volume'] >= 0)
    if df.empty:
        raise MarketDataError('La fonte non fornisce righe OHLC valide.')
    df.index.name = 'Date'
    return df
