# VISION

## En une phrase
Un **copilote financier personnel** qui agrège macro, marchés, et news, en fait des **insights actionnables** (CT/MT/LT), et permet d’**interroger des LLM** avec **≥5 ans de contexte**.

## Proposition de valeur
- **Tout-en-un** : macro (FRED), actions (yfinance), news (RSS/curation), Q&A LLM.
- **Signal > Bruit** : tri/dédup/scoring → Top 3 signaux & Top 3 risques.
- **Mémoire** : historisation pour RAG et suivi des thèses.
- **Traçabilité** : chaque sortie avec sources, dates, versions.

## Cibles & Horizons
- Court (jours/semaines), Moyen (mois), Long (trimestres/années).

## Piliers fonctionnels
1) Macro (FRED, VIX, GSCPI, GPR)
2) Actions (prix + indicateurs)
3) News (RSS robuste + scoring)
4) LLM Copilot (Q&A + what-if + RAG)
5) Mémoire & traçabilité

## Sorties
- **Market Brief** (hebdo/journalier)
- **Fiches Ticker**
- **Réponses LLM citées** (avec limites)

## KPIs initiaux
- Couverture ≥ 90% tickers ≤ 24h
- Fraîcheur news médiane < 10 min
- ≥ 80% Q&A avec ≥ 2 sources

## Garde-fous
Explainable-first, contre-arguments, opt-in Internet pour tests, citations obligatoires.

## MVP
- Ingestion macro/prix/news, dédup, scoring 40/40/20, brief hebdo, RAG 5 ans.

## V1
- Dashboard filtres (secteur, horizon, thème), alertes (SMA/RSI/sentiment/news), mini backtests, notes versionnées.

## V2
- Score apprenant (petit ML), calendrier événements, fondamentaux (si dispo), métriques de risque.

## Non-objectifs
Pas de trading auto, ni d’alpha opaque, ni de données payantes non conformes.
