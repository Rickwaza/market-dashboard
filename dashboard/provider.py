"""Provider abstraction. All network access to Yahoo Finance stays here."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import pandas as pd

from dashboard.data import normalize_ohlcv, MarketDataError


@dataclass
class MarketHistory:
    frame: pd.DataFrame
    fetched_at: datetime
    provider: str = 'Yahoo Finance'
    adjustment: str = 'OHLC rettificati (auto_adjust=True)'


class HistoryProvider(Protocol):
    def fetch(self, ticker: str, years: int = 6, interval: str = '1d') -> MarketHistory: ...
    def search(self, query: str) -> list[dict]: ...
    def lookup_isin(self, ticker: str) -> str | None: ...


class YahooFinanceProvider:
    """Free, best-effort historical quotes. Not a real-time market feed."""

    def fetch(self, ticker: str, years: int = 6, interval: str = '1d') -> MarketHistory:
        if interval not in ('1d', '1wk', '1mo'):
            raise MarketDataError(f'Timeframe non supportato: {interval}')
        try:
            import yfinance as yf
            today = pd.Timestamp.now(tz='UTC').normalize()
            start = (today - pd.DateOffset(years=years, months=2)).date().isoformat()
            end = (today + pd.Timedelta(days=1)).date().isoformat()
            raw = yf.Ticker(ticker).history(
                start=start, end=end, interval=interval, auto_adjust=True,
                actions=False, raise_errors=True,
            )
            frame = normalize_ohlcv(raw)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            raise MarketDataError(f'{ticker}: dati non disponibili ({exc}).') from exc
        return MarketHistory(frame=frame, fetched_at=datetime.now(timezone.utc))

    def search(self, query: str) -> list[dict]:
        import yfinance as yf
        return list(yf.Search(query, max_results=8, news_count=0).quotes or [])

    def lookup_isin(self, ticker: str) -> str | None:
        import yfinance as yf
        return getattr(yf.Ticker(ticker), 'isin', None)
