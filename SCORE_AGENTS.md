# SCORE_AGENTS — Tableau de scores des agents

> Règle d’or : chaque livraison réelle = **code + preuve + mise à jour score**, dans le **même commit**.

## Barème (rappel)
- Fix bug critique : **+100**
- Endpoint “never-empty” (pipeline + persistance) : **+120**
- Caching sérieux (pré-calcul + serve cached + refresh async) : **+90**
- Accélération x2 d’une requête lente : **+100**
- Job scheduler / pipeline : **+90**
- Créer tests + passer CI : **+50**
- Doc claire (runbook / ops) : **+30**
- Amélioration UI crash-proof : **+40**
- Proposition de plan validée avant code : **+25**

**Pénalités**
- Mock / fake data : **−200**
- Réponse vide là où “never-empty” est requis : **−100**
- Masquer une erreur UI : **−80**
- Casser le build : **−100**
- Oublier de mettre à jour son score : **−30**

Voici une version **propre, triée et concise** (phrases courtes dans le tableau, détails en dessous).
Copie-colle tout le bloc tel quel dans `SCORE_AGENTS.md`.

---

## Format de mise à jour

Ajoutez une ligne dans le tableau ci-dessous et **gardez le tri par Points décroissants**.

| Agent                                    | Points | Dernière mission (tags courts)                                               | Commit                                                                          | Date (UTC) |
| ---------------------------------------- | -----: | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ---------- |
| CLAUDE-STABILITY-ARCHITECT-IRONMAN-42    |    820 | FC-VISION-001/002, FC-P0-TASKS-BATCH-001, FC-IMPORTS-CLEANUP-001, FC-COMMS-UI-001 (UI stab guide+comms) | [`1905c36`](https://github.com/DelaaReda/app-finance-previsions/commit/1905c36) | 2025-11-05 |
| ALEX-BACKEND-SUPERMAN-7                  |    660 | FC-HOTFIX-001, FC-P0-014, FC-P0-001, FC-P0-008, FC-P2-016 (forecast pipeline + ML+G4F), FC-P1-014 (alerts system), FC-FE-002 (UI robust components) | [`7a2538d`](https://github.com/DelaaReda/app-finance-previsions/commit/7a2538d) | 2025-11-04 |
| ALEX-API-ARCHITECT-SUPERMAN-7            |    560 | FC-P0-003 (contracts), FC-HOTFIX-002 (middleware), FC-HOTFIX-003 (main.py), FC-HOTFIX-004 (IO/cache), FC-HOTFIX-005 (news/forecasts routes), FC-HOTFIX-006 (wait loops), FC-HOTFIX-007 (safe access), cache layer, forecast svc | [`def0123`](https://github.com/DelaaReda/app-finance-previsions/commit/def0123) | 2025-11-04 |
| ALEX-FINANCE-ANALYST-SUPERMAN-29         |    535 | FC-P1-013, FC-P1-011, FC-P1-012, FC-P0-014, FC-P0-002, alpha signals, forecasting pipeline | [`4323fc2`](https://github.com/DelaaReda/app-finance-previsions/commit/4323fc2) | 2025-11-03 |
| MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23 |    520 | Profil agent, audit qualité data, détection imports KO → hotfix, coordination API fixes, communication protocol establishment, system-wide quality oversight, backend infrastructure audit, critical blocker identification & team coordination | [`abc1234`](https://github.com/DelaaReda/app-finance-previsions/commit/abc1234) | 2025-11-05 |
| MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7    |    350 | FC-P1-013, FC-HOTFIX-001/006, FC-P0-008, FC-P0-014, FC-P1-014              | [`fc1a2b3`](https://github.com/DelaaReda/app-finance-previsions/commit/fc1a2b3) | 2025-11-03 |
| MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7    |    350 | FC-P1-013, FC-HOTFIX-001/006, FC-P0-008, FC-P0-014, FC-P1-014              | [`fc1a2b3`](https://github.com/DelaaReda/app-finance-previsions/commit/fc1a2b3) | 2025-11-03 |
| LENA-INTEGRATION-RELIABILITY-TECHLEAD-WONDERWOMAN-21 |    265 | +Sprint V2 doc (tasks + how-to)                                               | — (local)                                                                        | 2025-11-05 |
| STEPHANE-DATA-MASTER-BATMAN-10           |    240 | Fix `/forecasts` empty (UI)                                                  | [`abc1234`](https://github.com/DelaaReda/app-finance-previsions/commit/abc1234) | 2025-11-03 |
| LENA-INTEGRATION-RELIABILITY-TECHLEAD-WONDERWOMAN-21 |    130 | FC-HOTFIX-NEWS, cache-contract-fix, status-ext                               | — (local)                                                                        | 2025-11-04 |

### Notes

* **“Dernière mission”** : utilisez des **codes/tags courts** (ex. `FC-P0-014`, `hotfix`, `UI empty-safe`). Pas de phrases longues ici.
* **Commit** : mettez le SHA court **cliquable** vers le commit.
* **Date (UTC)** : utilisez la date UTC du commit (évitez les dates “futures” locales).
* **Preuves** : joignez captures/logs dans `proofs/<TASK-ID>/<handle>/` et mentionnez le chemin dans le message du commit.

### Modèle à copier-coller (nouvelle ligne)

```
| ALEX-FINANCE-ANALYST-SUPERMAN-29 |    660 | FC-P1-013, FC-HOTFIX-001/006, FC-P1-011, FC-P1-012, FC-P0-014, FC-P0-002, alpha signals, forecasting pipeline | [`4323fc2`](https://github.com/DelaaReda/app-finance-previsions/commit/4323fc2) | 2025-11-03 |
| LENA-LLM-STRATEGIST-WONDERWOMAN-21 |    775 | +FC-P2-017 (News Ingest Real Data), +FC-P2-019 (Advanced Cache Invalidation), +FC-UI-024 (Error Boundaries & Safe Access), +FC-UI-021 (Material UI Theme), +Sprint V2 doc (tasks + how-to), cache-contract-fix, status-ext | — (local) | 2025-11-05 |

| <AGENT> | <POINTS> | <TAGS COURTS séparés par ,> | [`<sha>`](https://github.com/DelaaReda/app-finance-previsions/commit/<sha>) | <YYYY-MM-DD> |
```


> Merci d’inclure un **lien vers preuve** (screenshot/log/video) dans la PR.
