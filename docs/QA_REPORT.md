### Sprint-5 — Rapport QA (26 octobre 2025)

📌 Version : v1.1
🧾 Auteur QA : ATLAS (Manager/QA Architect)
🗓️ Date : 2025-10-26

---

## Résumé exécutif

Sprint-5 livré à ~80%.

- Fusion importante : `feat/backtests-eval-pages` → `main` (merge `sprint-5 2/5`).
- Nouveaux artefacts ajoutés : pages `/backtests`, `/evaluation` et agents `backtest_agent`, `evaluation_agent`.
- Actions requises : validation UX complète (MCP + web_eval_agent), génération de données par les agents, et ajout d'artifacts/logs.
 - Actions requises : validation UX complète via `dash.testing`, génération de données par les agents, et ajout d'artifacts/logs.

---

## Commits examinés

| Commit | Objet | Commentaire |
|---|---|---|
| `3e0e235` | sprint-5 2/5: merge feat/backtests-eval-pages into main | Merge réalisé — à valider fonctionnellement (voir tests) |
| `ffa805a` | sprint-5 1/5 docs: update commit message policy to include sprint/progress | Doc mise à jour pour exigence sprint/progress |
| `8b27e9d` | feat(agents/pages): add backtest & evaluation agents and pages; docs + tests | Ajout des agents/pages; nécessite génération de données |
| `09e3ee6` | Sprint-5: QA report - 3/5 pages delivered, smoke tests 12/12 passing | QA report initial présent dans docs |

---

## Validation requise (actions QA)

1. Générer les données d'entrée pour les agents :

```bash
make equity-forecast && make forecast-aggregate
make macro-forecast && make update-monitor
```

2. Exécuter les agents Backtest & Evaluation (si cibles Make présentes) :

```bash
make backtest || PYTHONPATH=src python -m src.agents.backtest_agent --horizon 1m --top-n 5
make evaluate || PYTHONPATH=src python -m src.agents.evaluation_agent --horizon 1m
```

3. Vérifier la présence des sorties datées :

- `data/backtest/dt=YYYYMMDD/*` (details.parquet, summary.json)
- `data/evaluation/dt=YYYYMMDD/*` (metrics.json, details.parquet)

4. Démarrer l'UI et exécuter les tests automatisés :

```bash
make dash-restart-bg
make dash-smoke        # vérifie HTTP 200 sur routes connues
pytest -q              # exécute les tests unitaires
```

5. Exécuter les tests UI automatisés basés sur `dash.testing` :

```bash
# Activer les e2e Dash tests (les tests e2e sont gatés par la variable d'env)
ENABLE_DASH_E2E=1 pytest -q tests/e2e
```

6. (Optionnel) Évaluation MCP/Playwright (UX automatisée) :

Pré‑requis: Node/npm installés, Playwright MCP disponible.

```bash
make dash-mcp-test   # lance ops/ui/mcp_dash_smoke.mjs; produit un rapport et des captures
```

Sorties attendues:
- `data/reports/dt=YYYYMMDD/dash_smoke_mcp_report.json`
- `artifacts/smoke/dash_mcp/*.png` (captures par route)

7. Collecter et joindre les sorties :

- `logs/ui_tests.log` (stdout/stderr des tests UI)
- `artifacts/ui_eval/report.json` et `artifacts/ui_eval/screenshots/*` (si configurés par les tests dash.testing)
- Exemplaires de `data/backtest/dt=*/details.parquet` et `data/evaluation/dt=*/metrics.json` si possible

---

## Résultats attendus / Critères de succès

- Toutes les routes (incl. `/backtests`, `/evaluation`) répondent HTTP 200.
- Les DataTables et graphiques se chargent sans erreurs de callback.
- Fichiers datés produits par les agents (dt=YYYYMMDD) présents.
- Aucun stacktrace dans `logs/` et pas de secrets exposés.
- Les tests `dash.testing` produisent les rapports et screenshots attendus (artifacts/ui_eval/).

---

## Problèmes connus / Points de vigilance

- Vérifier idempotence des agents : n’écrivent que dans dt=today.
- Assurer que les agents loggent début/fin et warnings.
- Pages Dash doivent gérer état vide FR si pas de données.
- S’assurer d’éviter la duplication de logique avec les agents existants (ex. forecast aggregator).

---

## Recommandations & Next steps

1. Exécuter la séquence de validation ci‑dessus et joindre les logs/screenshots à ce rapport.
2. Si des erreurs apparaissent dans les tests dash.testing, ouvrir une bug PR avec les artefacts (screenshots + console errors) et les logs des tests.
3. Ajouter `data/backtest/` et `data/evaluation/` aux patterns de `.gitignore` si des fichiers temporaires locaux apparaissent par erreur.
4. Après validation, marquer Sprint-5 comme `4/5` dans `docs/PROGRESS.md` et appliquer le tag Git `sprint-5-complete` si souhaité.

---

_Fichier généré automatiquement par l’outil de support dev — compléter avec les artefacts et logs une fois les tests exécutés._
