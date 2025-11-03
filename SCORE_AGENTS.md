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

## Format de mise à jour
Ajoutez une ligne dans le tableau ci-dessous et **gardez le tri par Points décroissants**.

| Agent                          | Points | Dernière mission                            | Commit                  | Date (UTC) |
|--------------------------------|--------|---------------------------------------------|-------------------------|------------|
| STEPHANE-DATA-MASTER-BATMAN-10 | 240    | Fixed /forecasts empty response             | `abc1234`               | 2025-11-03 |
| REDA-API-MASTER-VENOM-7.       | 340    | Integrated api endpoit with reel data.....  | `abc123eeeaeda31232324` | 2025-11-03 |

> Merci d’inclure un **lien vers preuve** (screenshot/log/video) dans la PR.
