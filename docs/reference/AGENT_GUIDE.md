# AGENT GUIDE (LLM)

Ce document explique à un agent LLM comment contribuer efficacement au repo.

## Objectifs
- Implémenter des features qui améliorent le **signal** et l’**explainabilité**.
- Éviter les régressions réseau et garder les tests **opt-in**.

## Règles d’or
1. **Explainable-first** : chaque sortie doit citer ses sources (URL, série, date).
2. **Trace** : envelopper les I/O critiques avec `@trace_call`.
3. **Tests** :
   - Unit par défaut : `make test`
   - Intégration réseau opt-in : `make it-integration` avec `AF_ALLOW_INTERNET=1`
4. **Données** : Pas de providers payants non conformes. Préférer FRED/yfinance/RSS.
5. **RAG** : toute nouvelle donnée textuelle doit être indexable (métadonnées: date/source/ticker).

## Conventions
- **Scoring composite** : commencer par Macro(40) + Tech(40) + News(20).
- **Nom des jobs Makefile** : `smoke`, `test`, `it-integration`, `demo`.
- **Logs** : utiliser `core_runtime.log` (alias `apps.app.logger`).
- **Compat Streamlit** : utiliser `utils.st_compat` dans les tests.

## Roadmap dev (suggestions)
- `ingestion/finnews`: restaurer/déplacer la déduplication avec hash `(source|title|published)`.
- `apps/*`: générer un **Market Brief** hebdo exportable (HTML/MD) avec score composite.
- `research/*`: implémenter un RAG minimal (embeddings + store) sur news 12-24 mois + séries clés 5 ans.
- `alerts/*`: règles simples (RSI>70, croisement SMA, spike sentiment).

## Checklist PR
- [ ] Tests unit OK
- [ ] `it-integration` OK (si concerné)
- [ ] Logs/trace sur I/O
- [ ] Sources citées dans l’UI/rapport
- [ ] README/VISION à jour si besoin
