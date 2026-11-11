# Verifica locale del progetto MarketScope

Data esecuzione: 11 novembre 2026

## Ambiente disponibile

- Python 3.13.5
- Pandas 2.2.3
- NumPy 2.3.5
- Plotly 6.5.2
- pytest 9.0.2
- Streamlit: **non installato**
- yfinance: **non installato**
- Accesso ad un indice pip e alle API finanziarie esterne: **non disponibile**

## Verifiche realmente eseguite

- `python -m compileall -q .`: eseguito senza errori sintattici.
- `python -m pytest -q`: **31 test superati**.
- Costruzione di figure Plotly reali con dati OHLCV sintetici, incluso un grafico con candlestick, 3 SMA, EMA, Bande di Bollinger e volume, e un grafico VIX/HV con assi distinti: riuscita.
- Test del provider con un modulo yfinance simulato (`monkeypatch`): riusciti.
- Validazione degli ISIN con algoritmo Luhn: riuscita sugli esempi presenti nei test.
- Verifica di esportazione/importazione JSON, calcoli statistici e gestione di anomalie OHLCV: riuscita.

## Verifiche non eseguite

- Avvio reale della app con `streamlit run streamlit_app.py`.
- Rendering dell'interfaccia nel browser e test manuali responsive.
- Acquisizione di serie storiche live tramite Yahoo Finance, VIX incluso.
- Risoluzione ISIN contro le API effettivamente disponibili online.
- Pubblicazione su Streamlit Community Cloud.

L'assenza di test live non deve essere confusa con un successo o un insuccesso di queste funzionalita. I file forniti costituiscono un MVP implementato, ma la validazione end-to-end va completata in un ambiente con le dipendenze installate e accesso alla rete.
