# Sprint-5 (26 octobre 2025) — Note d'avancement

- ✅ Backtests & Evaluation pages livrées (Dash pages + agents correspondants)
- ✅ Tests ajoutés : unitaires + e2e (e2e gated par `ENABLE_DASH_E2E`)
- ✅ QA report: `docs/QA_REPORT.md` ajouté (instructions de validation)
- 🔲 Validation UX & données : en attente de génération des données et exécution des tests MCP/web-eval

Actions recommandées :

1. Générer les données et exécuter les agents :

```bash
make equity-forecast && make forecast-aggregate && make macro-forecast && make update-monitor
```

2. Redémarrer l'UI et lancer les smoke tests :

```bash
make dash-restart-bg
make dash-smoke
```

3. Pour les validations UX automatisées : lancer `make dash-mcp-test` ou exécuter `web_eval_agent` pour capturer screenshots et logs.

Notes : ajouter les dossiers générés `data/backtest/dt=*` et `data/evaluation/dt=*` à `.gitignore` pour éviter de versionner des artefacts locaux.
