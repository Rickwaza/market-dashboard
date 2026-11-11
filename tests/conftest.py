"""Synthetic market data: tests never require Yahoo network access."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def prices() -> pd.DataFrame:
    dates = pd.bdate_range(end=pd.Timestamp.now(tz='UTC').tz_localize(None).normalize(), periods=510)
    trend = 100.0 + np.arange(510) * 0.13
    movement = 2.0 * np.sin(np.arange(510) / 13)
    close = trend + movement
    return pd.DataFrame({
        'Open': close - 0.20,
        'High': close + 0.80,
        'Low': close - 1.0,
        'Close': close,
        'Volume': 100_000 + (np.arange(510) % 20) * 1_000,
    }, index=dates)
