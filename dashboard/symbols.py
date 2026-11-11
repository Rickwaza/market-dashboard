"""ISIN validation and cautious ticker identification."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Any

ISIN_RE = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
SYMBOL_RE = re.compile(r'^[A-Z0-9^][A-Z0-9^._=\-]{0,31}$')


def clean_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not SYMBOL_RE.fullmatch(normalized):
        raise ValueError('Ticker non valido: controlla il simbolo e il suffisso della borsa.')
    return normalized


def is_valid_isin(isin: str) -> bool:
    code = isin.strip().upper()
    if not ISIN_RE.fullmatch(code):
        return False
    digits = ''.join(str(int(char, 36)) if char.isalpha() else char for char in code)
    total = 0
    for idx, digit in enumerate(reversed(digits)):
        n = int(digit)
        if idx % 2 == 1:
            n *= 2
            n = n // 10 + n % 10
        total += n
    return total % 10 == 0


@dataclass(frozen=True)
class IsinCandidate:
    ticker: str
    name: str
    exchange: str
    verified: bool


def resolve_isin(
    isin: str,
    search_quotes: Callable[[str], list[dict[str, Any]]],
    lookup_isin: Callable[[str], str | None] | None = None,
) -> list[IsinCandidate]:
    """Search providers may omit ISIN. A guess is never marked verified."""
    code = isin.strip().upper()
    if not is_valid_isin(code):
        raise ValueError('Codice ISIN formalmente non valido.')
    results: list[IsinCandidate] = []
    seen: set[str] = set()
    for quote in search_quotes(code)[:8]:
        try:
            symbol = clean_symbol(str(quote.get('symbol') or ''))
        except ValueError:
            continue
        if symbol in seen:
            continue
        seen.add(symbol)
        supplied = str(quote.get('isin') or quote.get('ISIN') or '').upper()
        verified = supplied == code
        if not verified and lookup_isin is not None and len(results) < 4:
            try:
                verified = str(lookup_isin(symbol) or '').upper() == code
            except Exception:
                pass
        results.append(IsinCandidate(
            ticker=symbol,
            name=str(quote.get('shortname') or quote.get('longname') or symbol),
            exchange=str(quote.get('exchange') or 'Mercato non indicato'),
            verified=verified,
        ))
    return results
