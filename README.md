# MarketScope

Dashboard finanziaria interattiva e open source, sviluppata con **Python, Streamlit, Plotly, Pandas, NumPy e yfinance**.

**Stato del progetto:** MVP realizzato e verificato con test locali sui moduli indipendenti dall'interfaccia. Il funzionamento end-to-end su un ambiente Streamlit collegato a Yahoo Finance va verificato dopo l'installazione, perché l'ambiente di costruzione non disponeva dei pacchetti Streamlit/yfinance né di accesso alle API esterne.

## Funzionalita

- Tre strumenti iniziali: `AAPL`, `MSFT`, `SPY`. Puoi aggiungere/rimuovere/riordinare strumenti, massimo **sei**.
- Ingresso tramite ticker Yahoo Finance oppure ricerca tramite **ISIN**. Solo i risultati ISIN verificati sono identificati come tali. Le proposte non verificate richiedono una conferma esplicita.
- Fino a **sei grafici candlestick** simultanei, con volumi, pan/zoom e reset dello zoom nella barra strumenti Plotly.
- Disposizione a **1, 2 o 3 colonne** su desktop, con adattamento per schermi piccoli.
- Finestre temporali **1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y**, con selettore comune opzionale o periodi indipendenti per strumento.
- SMA/EMA multiple, periodo indipendente **5-200** sedute, fino a 12 medie per tipo e strumento.
- Bande di Bollinger configurabili: periodo 5-200, deviazione standard 0.1-5, riempimento opzionale.
- **Settimo pannello indipendente** dedicato al VIX (`^VIX`), massimo 3 anni, con soglie opzionali 15/20/30/40.
- Volatilita storica annualizzata degli strumenti con finestre di 20, 30 o 60 sedute.
- Session State, caching con TTL e aggiornamento manuale dei dati.
- Export/import JSON di strumenti, indicatori, periodi e layout.
- Modalita **Griglia** e **Dettaglio**.
- Tema scuro, messaggi di errore per dati non disponibili, indicazione delle date delle ultime rilevazioni.

## Architettura

```text
streamlit_app.py
    |
    +-- dashboard/ui.py            interfaccia Streamlit e controllo dello stato
    |      |
    |      +-- provider.py          protocollo HistoryProvider + YahooFinanceProvider
    |      |      +-- data.py       pulizia/normalizzazione OHLCV
    |      |
    |      +-- indicators.py        SMA, EMA, Bollinger, HV
    |      +-- indicator_registry.py registro calcoli e tipo pannello
    |      +-- charts.py            grafici Plotly e pannello VIX/HV
    |      +-- symbols.py           ISIN e ticker
    |      +-- settings.py          validazione, import, export preferenze
    |      +-- config.py            costanti e finestre storiche
    |
    +-- config/defaults.json       configurazione iniziale del repository
    +-- tests/                    test sintetici e mock provider
```

La separazione tra `HistoryProvider`, `normalize_ohlcv`, indicatori e grafici permette di cambiare l'origine delle serie storiche senza riscrivere il motore di visualizzazione. I calcoli lavorano su Pandas DataFrame OHLCV validati. La griglia e il pannello volatilita utilizzano `@st.fragment` per limitare i rerun e `@st.cache_data` per evitare download duplicati.

## Installazione locale

Richiede **Python 3.12** consigliato (3.11 o successivo con dipendenze compatibili). Esempio:

```bash
git clone https://github.com/USERNAME/market-dashboard.git
cd market-dashboard
python -m venv .venv
```

**Windows, PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

**macOS / Linux:**

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Apri l'URL locale mostrato nel terminale (solitamente `http://localhost:8501`). Per installare senza clonare, estrai lo ZIP allegato ed entra nella cartella del progetto. Nell'esempio `USERNAME` e soltanto un segnaposto, non un repository online gia pubblicato.

## Uso: strumenti e indicatori

1. La sidebar si apre con `AAPL`, `MSFT` e `SPY`.
2. Per aggiungere un ticker, scegli **Ticker**, inserisci ad esempio `NVDA`, `ENI.MI`, `BTC-USD` o `EURUSD=X` e conferma. La disponibilita effettiva dipende dal provider.
3. Per cercare tramite ISIN, scegli **ISIN** (esempio `US0378331005`) e avvia la ricerca. Se Yahoo non puo fornire una corrispondenza certa, inserisci il ticker manualmente oppure conferma consapevolmente un suggerimento **non verificato**. Un ISIN puo identificare uno strumento negoziato su diversi mercati, con ticker e valuta differenti.
4. Usa le frecce della sidebar per riordinare gli strumenti e **✕** per rimuoverli.
5. Espandi **Indicatori e intervallo** nel riquadro del titolo. Seleziona contemporaneamente SMA 20, 50 e 200, EMA 21 e Bande di Bollinger, oppure qualunque combinazione consentita.
6. Il pulsante **Aggiorna prezzi** forza un nuovo download (quando il provider risponde).
7. Seleziona **Dettaglio** per un solo grafico esteso. Nella barra strumenti Plotly puoi effettuare zoom, pan e reset delle scale.

**Intervalli condivisi:** abilitando "Intervallo comune per i titoli" si impone a tutti i grafici l'intervallo scelto. Lo zoom effettuato direttamente con il mouse sui singoli grafici **non** viene propagato agli altri nella prima versione. La modifica di SMA/EMA/BB non forza un nuovo download dello storico grazie alla cache.

## Politica dati, prezzi e volatilita

- **Fonte:** Yahoo Finance, tramite libreria non ufficiale `yfinance`.
- **Frequenza:** candele giornaliere (`1d`).
- **Prezzi:** `Ticker.history(..., auto_adjust=True, actions=False)`, che chiede al provider OHLC rettificati per split e dividendi; non si interpretino questi valori come i prezzi di scambio storici grezzi. I volumi sono conservati *come restituiti* dal provider, senza aggiustamenti effettuati da MarketScope. La comparabilita dei volumi attorno a operazioni societarie va verificata secondo lo strumento e la fonte.
- **Prezzo attuale:** la dashboard mostra **l'ultima chiusura storica disponibile**, non una quotazione real-time. La differenza percentuale usa la chiusura della riga precedente valida.
- **Riservatezza:** questa app non richiede credenziali di brokerage, conti, token o API a pagamento. I ticker richiesti sono inviati al provider dati.
- **Warm-up indicatori:** per una vista storica massima di 5 anni viene richiesto un intervallo di dati piu ampio (oltre 6 anni), per evitare SMA 200 artificiali all'estremo sinistro. Gli indicatori vengono calcolati **prima** del taglio alla finestra visibile. Se lo strumento non ha sufficiente storico, i risultati iniziali rimangono `NaN`.
- **SMA:** media aritmetica di `n` chiusure, disponibile solo dalla `n`-esima osservazione valida.
- **EMA:** inizializzazione con SMA delle prime `n` osservazioni, poi ricorsione con `alpha = 2/(n+1)`; dopo un prezzo mancante, il calcolo ricomincia con un nuovo warm-up.
- **Bollinger:** media semplice e `std(ddof=0)` delle chiusure nella finestra, banda alta e bassa = media ± moltiplicatore × deviazione standard. Le prime `n-1` righe sono non definite.
- **HV:** `r_t = ln(C_t/C_(t-1))`, `HV_t = std(r_{t-n+1}..r_t, ddof=1) * sqrt(sedute_annue) * 100`. Default **252**, modificabile da 200 a 366 per mercati con calendari differenti (crypto incluso).
- **VIX:** indice di volatilita **implicita** attesa derivata dalle opzioni sullo S&P 500, in punti indice. Non equivale alla volatilita **realizzata** dei titoli e non viene disegnato sullo stesso asse della HV. Le soglie 15/20/30/40 sono solo riferimenti pratici, non leggi statistiche.
- **Data e ora:** l'ora di download mostrata e convertita nel fuso Europe/Rome. La data di ultima seduta deriva dalla serie, non dall'ora del download.
- **Limitazioni:** Yahoo puo applicare limiti, ritardi, interruzioni, periodi storici diversi e variazioni delle condizioni d'uso. Alcuni prodotti non hanno volume o OHLC completi. Dati settimanali/mensili, ulteriori provider e nuovi indicatori sono estensioni architetturali, non funzioni gia implementate.

## Preferenze e deployment

Le impostazioni **iniziali** sono in `config/defaults.json`. Durante l'uso le modifiche vivono in `st.session_state`. Per mantenerle oltre la sessione, clicca **Esporta configurazione JSON**. Per ripristinarle, carica quel file tramite **Importa configurazione JSON**. Il contenuto importato viene validato e limitato a sei ticker, finestre e parametri supportati.

La dashboard **non** salva automaticamente le preferenze su disco cloud, browser storage o database. Dopo il riavvio senza import riparte dai valori iniziali del repository. Per persistenza automatica per utente servirebbe un backend duraturo con eventuale autenticazione.

Per pubblicare senza pagare un server Python:

1. Crea un repository GitHub e carica i file del progetto, mantenendo `.streamlit/config.toml`.
2. Visita https://share.streamlit.io/ ed esegui l'accesso con GitHub.
3. Seleziona **Create app**, repository, branch e `streamlit_app.py` come entrypoint.
4. Scegli Python **3.12** nelle impostazioni avanzate e pubblica. Streamlit installerà le dipendenze da `requirements.txt`.
5. Verifica la disponibilita di `AAPL`, `^VIX` e dei grafici, quindi prova l'import/export JSON.

**GitHub Pages non e adatto** ad eseguire una app Streamlit con backend Python, perche serve un processo server. Streamlit Community Cloud e un servizio distinto con piano gratuito e possibili limiti di risorse e disponibilita.

## Cache e prestazioni

Default TTL 900 secondi (15 minuti). Per cambiarlo **prima** di avviare Streamlit:

```bash
export MARKET_CACHE_TTL=600     # macOS/Linux
```

Su PowerShell:

```powershell
$env:MARKET_CACHE_TTL="600"
```

La cache e condivisa in base al ticker, alla lunghezza storica richiesta e al contatore degli aggiornamenti manuali. I pannelli di volatilita riutilizzano gli stessi dati richiesti dai grafici prezzi. L'aggiornamento manuale invalida logicamente i risultati della sessione aggiungendo un token di generazione alla chiave di cache, mentre le vecchie entry rimangono fino alla loro scadenza o espulsione.

## Test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Il repository include test su SMA, EMA, Bande di Bollinger, HV, serie troppo corte, dati assenti, normalizzazione, ISIN, preferenze, figure Plotly e provider simulato. I test in `tests/` **non** utilizzano la rete. Il workflow `.github/workflows/tests.yml` esegue gli stessi test su GitHub Actions.

Per la verifica **end-to-end** in un ambiente con Streamlit e accesso a Yahoo:

1. Esegui l'app in locale e controlla che compaiano i tre grafici iniziali e il settimo pannello.
2. Porta gli strumenti attivi a sei, con piu medie e Bollinger su ciascuno.
3. Verifica il cambio finestre 1M→5Y, l'aggiornamento, il reset degli zoom e la vista Dettaglio.
4. Modifica solo le medie di AAPL e verifica che MSFT e SPY mantengano i rispettivi indicatori.
5. Disabilita la connessione e verifica che un ticker inesistente sia gestito senza arrestare l'intera pagina.
6. Esporta le preferenze, importale in una nuova sessione e confronta grafici/periodi.

## Estensioni previste

Il provider implementa un protocollo (`HistoryProvider`) e puo essere sostituito. Per implementare RSI, MACD, ATR, VWAP e Stochastic occorre aggiungere i calcoli al motore `indicators.py`, registrarli in `indicator_registry.py` specificando se richiedono un pannello separato, completare la gestione dei pannelli secondari in `charts.py`, i controlli in `ui.py` e i test. **Non** sono inclusi nell'MVP. La granularita settimanale e mensile, l'autenticazione e la sincronizzazione dello zoom manuale richiedono ulteriori lavori.

## Uso responsabile

Questo software serve a fini informativi e didattici, non e consulenza di investimento e non e una fonte certificata per ordini o decisioni in tempo reale. Verifica condizioni d'uso e licenze dei dati del provider prima di distribuire pubblicamente l'app per usi non personali o commerciali.
