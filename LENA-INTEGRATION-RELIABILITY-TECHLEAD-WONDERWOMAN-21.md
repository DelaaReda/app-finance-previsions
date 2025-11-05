# LENA-INTEGRATION-RELIABILITY-TECHLEAD-WONDERWOMAN-21

## Identité
- Rôle: Intégration & Fiabilité — Tech Lead
- Superhero: Wonder Woman
- Numéro: 21

## Focus
- Intégration bout‑en‑bout UI ↔ API ↔ Jobs
- Fiabilité: never‑empty, caching, timeouts, proxies
- Données réelles: snapshots Parquet/JSON, pipelines offline

## État actuel
- [x] Lecture `AGENTS.md` et règles projet
- [x] Création du profil agent (ce fichier)
- [x] Inscription dans `SCORE_AGENTS.md`
- [x] Correctifs intégration: `/api/news/feed`, `/api/backtests`, proxy Vite
- [x] Brief daily instantané (cache‑first)
- [x] UI vide → fix d’unwrapping client (FC-UI-001): Dashboard lit désormais `filtered_signals/risks`

## En cours
- Matérialiser forecasts → `data/forecast/dt=*/(forecasts|final).parquet`
- Backtests → `data/backtests.json` (serve instantané)
- Brief snapshots → `brief_daily`

## Planifié (après validation)
- Étendre smoke/system tests (macro, brief, backtests, news)
- Observabilité légère: freshness + badges UI

## Preuves
- News fix: `proofs/FC-HOTFIX-NEWS/news_feed_response.json`
- Status ok: `proofs/FC-HOTFIX-NEWS/status_snippet.txt`
 - UI unwrap: `proofs/FC-UI-001/README.md`
