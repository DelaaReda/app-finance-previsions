# Partitions & Freshness — Guide rapide

Objectif: expliquer comment l’app structure ses sorties datées et comment vérifier la fraîcheur des données consommées par l’UI Dash.

- Convention des partitions
  - Tous les agents écrivent dans des dossiers datés: `data/<domaine>/dt=YYYYMMDD/`.
  - Exemples:
    - Prévisions actions: `data/forecast/dt=YYYYMMDD/forecasts.parquet` + `final.parquet`
    - Macro: `data/macro/forecast/dt=YYYYMMDD/macro_forecast.parquet`
    - Qualité: `data/quality/dt=YYYYMMDD/freshness.json` (et `report.json` si présent)

- Fichiers clés
  - `forecasts.parquet`: prévisions par ticker/horizon (1w/1m/1y), colonnes usuelles: `ticker, horizon, expected_return, confidence, direction`.
  - `final.parquet`: score agrégé (pondération des modèles/agents), ex: `final_score`.
  - `macro_forecast.parquet`: indicateurs macro clés (CPI YoY, pente 10Y–2Y, prob. récession), autres séries selon disponibilité.
  - `freshness.json`: synthèse des contrôles de fraicheur/couverture. Champs courants:
    - `checks.forecasts_today`, `checks.final_today`, `checks.macro_today` (booléens)
    - `checks.prices_5y_coverage_ratio` (0–1)
    - `latest_dt` (ISO date de la dernière partition connue)

- Vérifier rapidement la fraîcheur
  1. Générer les données du jour:
     ```bash
     make equity-forecast && make forecast-aggregate
     make macro-forecast && make update-monitor
     ```
  2. Ouvrir `/agents` et `/quality` dans l’UI Dash:
     - Dernières partitions listées + flags d’aujourd’hui
     - Tableau des anomalies (s’il y en a)
  3. Badge global (sidebar):
     - 🟢 HTTP OK + fraîcheur < 25h
     - 🟡 HTTP OK mais données anciennes
     - 🔴 serveur down

- Conseils
  - Toujours privilégier la dernière partition (`dt` la plus récente) — l’UI Dash fait ce choix par défaut.
  - En cas d’absence de fichiers, les pages affichent des états vides FR (pas d’exception).
  - Pour des tests locaux reproductibles, vous pouvez créer des partitions “factices” (ex: `dt=99999999`) avec un petit parquet minimal.

