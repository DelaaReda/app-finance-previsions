# DATA_AGENT_BRIEF.md

## Mission
Fiabiliser la qualité minimale des données MVP.

## Scope
- jobs ingestion liés aux endpoints MVP
- payloads JSON dans `copilot-app/backend/data/`

## Checks obligatoires
- champs essentiels non nuls
- timestamps présents
- flag `is_fallback` quand données de secours
- cohérence minimale des types

## Validation
- Générer un mini rapport qualité (ok/degraded/fallback)
- Aucun crash job sur run standard
