"""Streamlit presentation layer. No provider calls from chart builders."""
from __future__ import annotations

import json
from zoneinfo import ZoneInfo

import streamlit as st

from dashboard.charts import build_price_figure, build_volatility_figure
from dashboard.config import (
    CACHE_TTL_SECONDS, DEFAULT_CHART, MAX_INSTRUMENTS,
    TIME_WINDOWS, VIX_WINDOWS,
)
from dashboard.data import MarketDataError
from dashboard.indicators import historical_volatility
from dashboard.provider import MarketHistory, YahooFinanceProvider
from dashboard.settings import default_preferences, export_preferences, validate_chart, validate_preferences
from dashboard.symbols import clean_symbol, resolve_isin, is_valid_isin


@st.cache_data(ttl=CACHE_TTL_SECONDS, max_entries=128, show_spinner=False)
def cached_history(ticker: str, years: int, refresh_generation: int, interval: str = '1d') -> MarketHistory:
    """Data cache is shared across chart fragments and reused by HV computations."""
    return YahooFinanceProvider().fetch(ticker, years=years, interval=interval)


def init_session() -> None:
    if 'prefs' not in st.session_state:
        st.session_state['prefs'] = default_preferences()
    if st.session_state.pop('_reset_ui_next_run', False):
        clear_presentation_keys()
    if 'refresh_generation' not in st.session_state:
        st.session_state['refresh_generation'] = 0


def add_instrument(ticker: str, metadata: dict | None = None) -> bool:
    prefs = st.session_state['prefs']
    symbol = clean_symbol(ticker)
    if symbol in prefs['instruments']:
        st.sidebar.info(f'{symbol} e gia presente.')
        return False
    if len(prefs['instruments']) >= MAX_INSTRUMENTS:
        st.sidebar.error('Massimo 6 strumenti. Rimuovine uno prima di aggiungerne altri.')
        return False
    prefs['instruments'].append(symbol)
    prefs['charts'][symbol] = validate_chart(DEFAULT_CHART)
    if metadata:
        prefs.setdefault('metadata', {})[symbol] = metadata
    return True


def clear_presentation_keys() -> None:
    """Avoid stale widget state overriding the newly imported JSON preferences."""
    for key in list(st.session_state.keys()):
        if key.startswith('ui_') or key.startswith('chart_'):
            del st.session_state[key]


def render_sidebar() -> None:
    prefs = st.session_state['prefs']
    with st.sidebar:
        st.header('Configurazione')
        st.caption('Fino a 6 strumenti. Dati Yahoo Finance non garantiti in tempo reale.')
        with st.form('new_instrument', clear_on_submit=True):
            kind = st.radio('Aggiungi usando', ['Ticker', 'ISIN'], horizontal=True)
            value = st.text_input('Identificativo', placeholder='AAPL oppure US0378331005').strip()
            submitted = st.form_submit_button('Aggiungi / cerca', use_container_width=True)
        if submitted and value:
            if kind == 'Ticker':
                try:
                    if add_instrument(value):
                        st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            else:
                if not is_valid_isin(value):
                    st.error('ISIN non valido (formato o cifra di controllo).')
                else:
                    try:
                        with st.spinner('Ricerca ISIN sul provider...'):
                            provider = YahooFinanceProvider()
                            options = resolve_isin(value, provider.search, provider.lookup_isin)
                        if len([x for x in options if x.verified]) == 1:
                            chosen = next(x for x in options if x.verified)
                            if add_instrument(chosen.ticker, {
                                'isin': value.upper(), 'verified': True,
                                'name': chosen.name, 'exchange': chosen.exchange,
                            }):
                                st.session_state.pop('pending_isin', None)
                                st.rerun()
                        else:
                            st.session_state['pending_isin'] = {
                                'query': value.upper(),
                                'options': [vars(c) for c in options],
                            }
                    except Exception as exc:
                        st.warning(f'Ricerca ISIN non disponibile: {exc}. Inserisci il ticker manualmente.')
        pending = st.session_state.get('pending_isin')
        if pending:
            options = pending['options']
            st.info(f"Ricerca {pending['query']}: le proposte non verificate non devono essere considerate corrispondenze certe.")
            if options:
                labels = [
                    f"{item['ticker']} | {item['exchange']} | "
                    f"{'ISIN verificato' if item['verified'] else 'da verificare'}"
                    for item in options
                ]
                choice = st.selectbox('Risultati possibili', list(range(len(options))),
                                      format_func=lambda n: labels[n], key='ui_isin_candidate')
                if st.button('Conferma ticker selezionato', use_container_width=True):
                    item = options[choice]
                    metadata = {
                        'name': item['name'], 'exchange': item['exchange'],
                        'verified': bool(item['verified']),
                    }
                    if item['verified']:
                        metadata['isin'] = pending['query']
                    if add_instrument(item['ticker'], metadata):
                        st.session_state.pop('pending_isin', None)
                        st.rerun()
            else:
                st.warning('Nessuna proposta disponibile. Usa il ticker manuale.')
            if st.button('Annulla ricerca ISIN'):
                st.session_state.pop('pending_isin', None)
                st.rerun()

        st.divider()
        st.subheader(f"Strumenti: {len(prefs['instruments'])}/{MAX_INSTRUMENTS}")
        if prefs['instruments']:
            selected = st.selectbox('Seleziona per riordinare/rimuovere', prefs['instruments'], key='ui_edit_symbol')
            col_up, col_down, col_rm = st.columns(3)
            def move(delta: int) -> None:
                a = prefs['instruments']
                i = a.index(selected)
                j = i + delta
                if 0 <= j < len(a):
                    a[i], a[j] = a[j], a[i]
                    st.rerun()
            with col_up:
                st.button('↑', help='Sposta in alto', on_click=move, args=(-1,), use_container_width=True)
            with col_down:
                st.button('↓', help='Sposta in basso', on_click=move, args=(1,), use_container_width=True)
            with col_rm:
                if st.button('✕', help='Rimuovi strumento', use_container_width=True):
                    prefs['instruments'].remove(selected)
                    prefs['charts'].pop(selected, None)
                    prefs.get('metadata', {}).pop(selected, None)
                    st.session_state['_reset_ui_next_run'] = True
                    st.rerun()
        else:
            st.warning('Aggiungi almeno uno strumento per vedere i grafici.')

        st.divider()
        prefs['columns'] = st.select_slider('Colonne su desktop', options=[1, 2, 3],
                                             value=prefs['columns'], key='ui_columns')
        prefs['sync_periods'] = st.toggle('Intervallo comune per i titoli', value=prefs['sync_periods'],
                                           key='ui_sync_periods')
        if prefs['sync_periods']:
            prefs['global_period'] = st.selectbox('Intervallo titoli', list(TIME_WINDOWS),
                index=list(TIME_WINDOWS).index(prefs['global_period']), key='ui_global_period')
        if st.button('Aggiorna prezzi', use_container_width=True, icon='🔄'):
            st.session_state['refresh_generation'] += 1
            st.rerun()
        st.caption(f'Cache con scadenza: {CACHE_TTL_SECONDS // 60} minuti. Aggiornamento manuale disponibile.')

        st.divider()
        st.subheader('Preferenze')
        st.download_button(
            'Esporta configurazione JSON', data=export_preferences(prefs),
            file_name='market-dashboard-prefs.json', mime='application/json',
            use_container_width=True,
        )
        upload = st.file_uploader('Importa configurazione JSON', type=['json'], key='prefs_uploader')
        if st.button('Carica configurazione', disabled=upload is None, use_container_width=True):
            try:
                assert upload is not None
                parsed = json.loads(upload.getvalue().decode('utf-8'))
                st.session_state['prefs'] = validate_preferences(parsed)
                st.session_state.pop('pending_isin', None)
                st.session_state['_reset_ui_next_run'] = True
                st.rerun()
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                st.error(f'Configurazione non valida: {exc}')
        st.caption('Le preferenze non sono salvate automaticamente sul server. Esporta il JSON per conservarle oltre la sessione.')


@st.fragment
def render_instrument(ticker: str, expanded: bool = False) -> None:
    prefs = st.session_state['prefs']
    cfg = validate_chart(prefs['charts'].get(ticker, {}))
    title = ticker
    info = prefs.get('metadata', {}).get(ticker, {})
    if info.get('name'):
        title += f" · {info['name']}"
    st.subheader(title)
    with st.expander('Indicatori e intervallo', expanded=False):
        if not prefs['sync_periods']:
            cfg['period'] = st.selectbox('Periodo', list(TIME_WINDOWS),
                index=list(TIME_WINDOWS).index(cfg['period']), key=f'chart_{ticker}_period')
        st.caption('Attiva piu medie contemporaneamente. Parametri in sedute di mercato.')
        cfg['sma'] = st.multiselect('Medie semplici (SMA)', list(range(5, 201)),
                                     default=cfg['sma'], key=f'chart_{ticker}_sma', max_selections=12)
        cfg['ema'] = st.multiselect('Medie esponenziali (EMA)', list(range(5, 201)),
                                     default=cfg['ema'], key=f'chart_{ticker}_ema', max_selections=12)
        cfg['bollinger'] = st.toggle('Bande di Bollinger', value=cfg['bollinger'],
                                       key=f'chart_{ticker}_bb')
        b1, b2 = st.columns(2)
        with b1:
            cfg['bb_period'] = st.number_input('Periodo BB', 5, 200, cfg['bb_period'],
                key=f'chart_{ticker}_bb_period', disabled=not cfg['bollinger'])
        with b2:
            cfg['bb_std'] = st.number_input('Deviazioni standard', min_value=.1, max_value=5.0,
                value=float(cfg['bb_std']), step=.1, format='%.1f', key=f'chart_{ticker}_bb_std',
                disabled=not cfg['bollinger'])
        cfg['bb_fill'] = st.toggle('Riempimento bande', value=cfg['bb_fill'],
            key=f'chart_{ticker}_bb_fill', disabled=not cfg['bollinger'])
    prefs['charts'][ticker] = cfg
    period = prefs['global_period'] if prefs['sync_periods'] else cfg['period']
    try:
        with st.spinner(f'Dati {ticker}...'):
            history = cached_history(ticker, 6, st.session_state['refresh_generation'])
        frame = history.frame
        if len(frame) >= 2:
            close, previous = frame['Close'].iloc[-1], frame['Close'].iloc[-2]
            change = (close / previous - 1) * 100
            m1, m2 = st.columns(2)
            m1.metric('Ultima chiusura', f'{close:,.3f}', delta=f'{change:+.2f}%')
            m2.metric('Ultima seduta', str(frame.index[-1].date()))
        else:
            st.warning('Serie insufficiente per calcolare la variazione giornaliera.')
        fig = build_price_figure(frame, ticker, cfg, period, expanded)
        st.plotly_chart(fig, width='stretch', theme=None, key=f'plot_{ticker}',
            config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': True})
        local_time = history.fetched_at.astimezone(ZoneInfo('Europe/Rome'))
        st.caption(f"Fonte: {history.provider} | Download: {local_time:%d/%m/%Y %H:%M} (ora italiana) | Prezzi rettificati. Volume come fornito dalla fonte.")
        if frame['Volume'].isna().all():
            st.caption('Questo strumento non dispone del volume presso il provider.')
    except MarketDataError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f'Impossibile visualizzare {ticker}: {exc}')


@st.fragment
def render_volatility() -> None:
    prefs = st.session_state['prefs']
    st.subheader('VIX e volatilita storica')
    c1, c2, c3, c4 = st.columns([1.1, 1, 1, 1.2])
    with c1:
        prefs['vix_period'] = st.selectbox('Storico volatilita', VIX_WINDOWS,
            index=VIX_WINDOWS.index(prefs['vix_period']), key='ui_vix_period')
    with c2:
        prefs['vol_window'] = st.selectbox('Finestra HV', [20, 30, 60],
            index=[20, 30, 60].index(prefs['vol_window']), key='ui_vol_window')
    with c3:
        prefs['sessions_per_year'] = st.number_input('Sedute/anno', 200, 366,
            prefs['sessions_per_year'], key='ui_sessions_year')
    with c4:
        prefs['vix_thresholds'] = st.toggle('Soglie VIX indicative', value=prefs['vix_thresholds'],
                                              key='ui_vix_thresholds')
    vix_frame = None
    vix_error = None
    try:
        vix_history = cached_history('^VIX', 4, st.session_state['refresh_generation'])
        vix_frame = vix_history.frame
        st.metric('Ultimo VIX disponibile', f"{vix_frame['Close'].iloc[-1]:.2f} punti",
                  help=f"Rilevazione: {vix_frame.index[-1].date()}. Non e una quotazione in tempo reale.")
        st.caption(f'VIX: ultima seduta {vix_frame.index[-1]:%d/%m/%Y}. Dati storici non garantiti in tempo reale.')
    except MarketDataError as exc:
        vix_error = str(exc)
    except Exception as exc:
        vix_error = f'Errore VIX: {exc}'
    if vix_error:
        st.warning(vix_error)
    historical = {}
    failures = []
    for ticker in prefs['instruments']:
        try:
            history = cached_history(ticker, 6, st.session_state['refresh_generation'])
            series = historical_volatility(history.frame['Close'], prefs['vol_window'],
                                           prefs['sessions_per_year'])
            if series.notna().any():
                historical[ticker] = series
            else:
                failures.append(f'{ticker}: serie troppo corta')
        except Exception:
            failures.append(f'{ticker}: dati non disponibili')
    if failures:
        st.caption('HV non calcolabile per: ' + ', '.join(failures))
    figure = build_volatility_figure(vix_frame, historical, prefs['vix_period'],
                                     prefs['vol_window'], prefs['vix_thresholds'])
    st.plotly_chart(figure, width='stretch', theme=None, key='volatility_panel',
                    config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': True})
    st.caption('VIX: indice di volatilita implicita attesa su opzioni S&P 500 (scala in punti). '
               'HV: deviazione standard dei rendimenti logaritmici, annualizzata e moltiplicata per 100 (scala in %). '
               'Le misure non sono intercambiabili. Le soglie 15/20/30/40 sono riferimenti orientativi.')


def main() -> None:
    st.set_page_config(page_title='MarketScope | Dashboard finanziaria',
                       page_icon='📈', layout='wide', initial_sidebar_state='expanded')
    st.markdown('''<style>
    .block-container {padding-top: 1.3rem; max-width: 1850px;}
    h1, h2, h3 {letter-spacing: -.025em;}
    div[data-testid="stMetric"] {background:#151f32; border:1px solid #273750;
        border-radius:12px; padding: 9px 12px;}
    @media (max-width: 800px) {
       div[data-testid="stHorizontalBlock"] {flex-wrap:wrap !important;}
       div[data-testid="stColumn"] {min-width:min(100%,340px) !important;flex:1 1 340px !important;}
       .block-container {padding-left: 0.7rem; padding-right: 0.7rem;}
    }
    </style>''', unsafe_allow_html=True)
    init_session()
    render_sidebar()
    prefs = st.session_state['prefs']
    st.title('MarketScope')
    st.caption('Dashboard multi-strumento | Candlestick, volumi, indicatori, VIX e volatilita storica')
    mode = st.radio('Vista', ['Griglia', 'Dettaglio'], horizontal=True, key='ui_view_mode')
    tickers = prefs['instruments']
    if mode == 'Dettaglio' and tickers:
        focused = st.selectbox('Strumento in dettaglio', tickers, key='ui_focused')
        render_instrument(focused, expanded=True)
    elif tickers:
        columns = min(prefs['columns'], len(tickers))
        for i in range(0, len(tickers), columns):
            row = st.columns(columns, gap='medium')
            for j, column in enumerate(row):
                index = i + j
                if index < len(tickers):
                    with column:
                        with st.container(border=True):
                            render_instrument(tickers[index])
    else:
        st.info('Non ci sono strumenti selezionati. Aggiungine uno dalla barra laterale.')
    st.divider()
    with st.container(border=True):
        render_volatility()
    st.caption('Uso informativo, non costituisce consulenza finanziaria. '
               'Yahoo Finance puo applicare ritardi, limiti di frequenza e restrizioni di utilizzo. '
               'Nessun dato viene dichiarato real-time.')


if __name__ == '__main__':
    main()
