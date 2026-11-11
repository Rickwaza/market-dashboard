"""All Plotly construction is independent of Streamlit and data providers."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.config import CHART_COLORS, beginning_of_window, display_window
from dashboard.indicator_registry import indicator

GREEN = '#22c55e'
RED = '#ef4444'
BG = '#101827'
TEXT = '#dce6f5'
GRID = '#304057'


def _layout(fig: go.Figure, height: int, revision: str) -> None:
    fig.update_layout(
        template='plotly_dark', paper_bgcolor=BG, plot_bgcolor=BG,
        font={'color': TEXT, 'size': 11}, margin={'l': 35, 'r': 20, 't': 23, 'b': 25},
        hovermode='x', dragmode='zoom', height=height,
        legend={'orientation': 'h', 'y': 1.04, 'x': 0, 'font': {'size': 10}},
        uirevision=revision, modebar_add=['resetScale2d'],
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, rangeslider_visible=False, showspikes=True)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, fixedrange=False)


def build_price_figure(frame: pd.DataFrame, ticker: str, cfg: dict, period: str, expanded: bool = False) -> go.Figure:
    """Compute overlays on *full* history, then mask to the visible window."""
    visible = display_window(frame, period)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.055,
        row_heights=[0.77, 0.23],
    )
    if visible.empty:
        fig.add_annotation(text='Nessun dato nell\'intervallo selezionato', showarrow=False)
        _layout(fig, 570 if expanded else 445, ticker + period)
        return fig

    hover = []
    for dt, row in visible.iterrows():
        vol = f"{row['Volume']:,.0f}" if pd.notna(row['Volume']) else 'non disponibile'
        hover.append(
            f"{dt:%d/%m/%Y}<br>Open: {row['Open']:,.3f}<br>High: {row['High']:,.3f}"
            f"<br>Low: {row['Low']:,.3f}<br>Close: {row['Close']:,.3f}<br>Volume: {vol}"
        )
    fig.add_trace(go.Candlestick(
        x=visible.index, open=visible['Open'], high=visible['High'],
        low=visible['Low'], close=visible['Close'],
        increasing_line_color=GREEN, increasing_fillcolor=GREEN,
        decreasing_line_color=RED, decreasing_fillcolor=RED,
        text=hover, hoverinfo='text', name=ticker, showlegend=False,
    ), row=1, col=1)

    close = frame['Close']
    for n, kind in [(n, 'SMA') for n in cfg['sma']] + [(n, 'EMA') for n in cfg['ema']]:
        color_index = (cfg['sma'].index(n) if kind == 'SMA' else len(cfg['sma']) + cfg['ema'].index(n))
        series = indicator(kind.lower()).compute(close, n).reindex(visible.index)
        fig.add_trace(go.Scatter(
            x=visible.index, y=series, mode='lines', name=f'{kind} {n}',
            line={'color': CHART_COLORS[color_index % len(CHART_COLORS)], 'width': 1.55},
            hovertemplate=f'{kind} {n}: %{{y:,.3f}}<extra></extra>',
        ), row=1, col=1)

    if cfg['bollinger']:
        bb = indicator('bollinger').compute(close, cfg['bb_period'], cfg['bb_std']).reindex(visible.index)
        fill = 'tonexty' if cfg['bb_fill'] else None
        fig.add_trace(go.Scatter(
            x=visible.index, y=bb['lower'], mode='lines', name='BB inferiore',
            line={'color': '#a78bfa', 'width': 1, 'dash': 'dot'},
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=visible.index, y=bb['upper'], mode='lines', name='BB superiore',
            line={'color': '#a78bfa', 'width': 1, 'dash': 'dot'},
            fill=fill, fillcolor='rgba(167,139,250,.10)',
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=visible.index, y=bb['middle'], mode='lines', name=f"BB media {cfg['bb_period']}",
            line={'color': '#d8b4fe', 'width': 1.2},
        ), row=1, col=1)

    if visible['Volume'].notna().any():
        colors = [GREEN if row.Close >= row.Open else RED for row in visible.itertuples()]
        fig.add_trace(go.Bar(
            x=visible.index, y=visible['Volume'], marker_color=colors,
            marker_opacity=.75, name='Volume', showlegend=False,
            hovertemplate='Volume: %{y:,.0f}<extra></extra>',
        ), row=2, col=1)
    else:
        fig.add_annotation(text='Volume non disponibile', x=.5, y=.08,
                           xref='paper', yref='paper', showarrow=False)

    _layout(fig, 650 if expanded else 490, ticker + '_' + period)
    fig.update_yaxes(title_text='Prezzo', row=1, col=1)
    fig.update_yaxes(title_text='Vol.', row=2, col=1)
    fig.update_xaxes(range=[beginning_of_window(period), pd.Timestamp.now(tz='UTC').tz_localize(None) + pd.Timedelta(days=1)], row=2, col=1)
    return fig


def build_volatility_figure(
    vix_frame: pd.DataFrame | None,
    historical: dict[str, pd.Series],
    period: str,
    window: int,
    thresholds: bool,
) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.1,
                        row_heights=[.53, .47], subplot_titles=('VIX (punti indice)', f'Volatilita storica annualizzata, {window} sedute (%)'))
    if vix_frame is not None and not vix_frame.empty:
        vix = display_window(vix_frame, period)
        fig.add_trace(go.Scatter(x=vix.index, y=vix['Close'], mode='lines', name='VIX',
                                 line={'color': '#fb7185', 'width': 2.0},
                                 hovertemplate='VIX: %{y:.2f} punti<extra></extra>'), row=1, col=1)
        if thresholds:
            for level in (15, 20, 30, 40):
                fig.add_hline(y=level, row=1, col=1, line={'color': '#94a3b8', 'width': .8, 'dash': 'dot'},
                              annotation_text=f'{level}', annotation_position='right')
    else:
        fig.add_annotation(text='VIX non disponibile', x=.5, y=.78, xref='paper', yref='paper', showarrow=False)
    for i, (ticker, series) in enumerate(historical.items()):
        visible = display_window(series.to_frame('HV'), period)
        fig.add_trace(go.Scatter(
            x=visible.index, y=visible['HV'], name=f'HV {ticker}', mode='lines',
            line={'color': CHART_COLORS[i % len(CHART_COLORS)], 'width': 1.7},
            hovertemplate=f'HV {ticker}: %{{y:.2f}}%<extra></extra>',
        ), row=2, col=1)
    if not historical:
        fig.add_annotation(text='Volatilita storica non disponibile', x=.5, y=.25,
                           xref='paper', yref='paper', showarrow=False)
    _layout(fig, 590, 'vol_' + period + '_' + str(window))
    fig.update_yaxes(title_text='Punti', row=1, col=1)
    fig.update_yaxes(title_text='%', ticksuffix='%', row=2, col=1)
    fig.update_xaxes(range=[beginning_of_window(period), pd.Timestamp.now(tz='UTC').tz_localize(None) + pd.Timedelta(days=1)], row=2, col=1)
    return fig
