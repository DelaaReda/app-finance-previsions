# Nightly ROI — Orchestrator Improvements

## Changelog
- Initialized.

## 2026-02-24 22:30 (America/New_York)
NO_DELTA

Raison: aucune donnée opérationnelle exploitable ajoutée depuis l’initialisation (`findings.md`, `improvements.md`, `experiments.md` contiennent uniquement "Initialized."). Impossible de classer un Top 5 ROI sans nouveaux signaux (incidents, fréquences, effort observé, résultats d’expériences).

## 2026-02-24 22:50 (America/New_York)
Top 5 améliorations ROI — Sprint SPRINT-2026-W09

1) Préflight bloquant sur état de queue invalide
- problème: `BATCH-01` rejeté (`invalid state IN_SPRINT`) => aucun lot ne démarre.
- cause: désalignement entre les états autorisés par `scripts/preflight_dispatch.sh` et `docs/orchestrator-ops/priority-queue.json`.
- action: définir un enum d’états unique + validation JSON (CI locale) + auto-correction vers état valide suggéré.
- effort: S
- impact: Très élevé (débloque tout le flux de delivery).
- risque: Faible (changement local de validation).
- rollback: désactiver validation stricte et revenir au mapping précédent.
- owner_role: architect

2) Path runtime non portable (macOS hardcodé sur VM Linux)
- problème: `--tmux-cmd status` échoue (`PROJECT_DIR introuvable: /Users/venom/Documents/analyse-financiere`).
- cause: variable/config `PROJECT_DIR` figée pour macOS.
- action: rendre `PROJECT_DIR` dérivé du repo courant (fallback `pwd`) + override explicite via env.
- effort: S
- impact: Élevé (restaure observabilité watchdog et contrôle tmux).
- risque: Moyen (peut casser un setup existant si fallback mal priorisé).
- rollback: restaurer résolution path précédente via flag `LEGACY_PROJECT_DIR=1`.
- owner_role: backend

3) Bruit de commits NO_DELTA
- problème: commits inutiles quand aucun nouveau signal, dilution de l’historique utile.
- cause: absence de garde « no-op » avant persistance/commit.
- action: gate de changement de contenu (hash diff) + skip commit automatique si NO_DELTA.
- effort: S
- impact: Élevé (réduit bruit, améliore lisibilité et coût review).
- risque: Faible.
- rollback: forcer commit via option manuelle `--allow-empty-report`.
- owner_role: manager

4) Cadence cron trop agressive => spikes rate-limit
- problème: saturation intermittente, baisse de débit utile.
- cause: fréquence fixe non adaptative malgré signaux de throttling.
- action: auto-throttle exponentiel (cooldown + jitter) basé sur erreurs rate-limit détectées.
- effort: M
- impact: Élevé (stabilité + meilleure utilisation quota).
- risque: Moyen (latence accrue sur runs non urgents).
- rollback: revenir à intervalle fixe actuel.
- owner_role: manager

5) Gate de complétude des preuves absente
- problème: lots suivants (ex. Batch-02) bloqués faute d’artefact PASS exploitable.
- cause: aucun contrôle systématique « artefact attendu présent + valide ».
- action: script `proof-completeness` avant promotion READY→IN_SPRINT, vérifiant artefacts batch requis.
- effort: M
- impact: Élevé (évite blocages en chaîne et faux démarrages).
- risque: Moyen (faux positifs si règles trop strictes).
- rollback: exécuter gate en mode warning-only.
- owner_role: qa

Priorités proposées pour le prochain daily scrum (Top 3)
1. Débloquer immédiatement le flux: corriger l’état `BATCH-01` + harmoniser enum queue/preflight.
2. Restaurer la supervision: corriger la résolution portable de `PROJECT_DIR` pour watchdog/tmux.
3. Réduire le gaspillage opérationnel: activer auto-throttle cron + skip commit NO_DELTA.

## 2026-02-24 23:59 (America/New_York)
Top 5 améliorations ROI — Sprint SPRINT-2026-W09

Delta observé depuis 22:50: `python3 scripts/qwen_orchestrator.py --tmux-cmd status` = **PASS** (rôles `planner/dev/tester/qa` UP), `bash scripts/preflight_dispatch.sh` = **PASS** (`health=UP`), mais **aucun** artefact `batch-01-*.md` présent dans `finance-app/openclaw-gates`.

1) Convertir le déblocage infra en premier DONE réel (Batch-01)
- problème: système prêt (tmux + preflight PASS) mais sprint toujours à `DONE: none`.
- cause: absence de déclenchement discipliné « un lot focalisé + preuve » juste après levée des blocants.
- action: lancer immédiatement un Batch-01 strictement focalisé A1 (`/api/health` + tests), exiger artefact `batch-01-<timestamp>.md` puis mise à jour board.
- effort: S
- impact: Très élevé (premier DONE sprint + déverrouillage séquentiel des dépendances).
- risque: Moyen (pression de vitesse sur qualité si scope dérive).
- rollback: annuler le lot via revert git ciblé + remettre item en READY avec scope réduit.
- owner_role: planner

2) Gate « preuve obligatoire » pour transitions de lot
- problème: `BATCH-02` reste bloqué tant que la preuve PASS `BATCH-01` est absente.
- cause: contrôle de complétude encore manuel et tardif.
- action: imposer script `proof-completeness` sur transition READY→IN_SPRINT (artefact batch requis + champs DoD complets).
- effort: M
- impact: Élevé (réduit blocages en chaîne et faux démarrages).
- risque: Moyen (rejets initiaux plus fréquents).
- rollback: mode `warn-only` pendant 1 sprint.
- owner_role: qa

3) Appliquer strictement WIP P0=2 pendant la remise en flux
- problème: A1/A2/C1 simultanés avec throughput nul au snapshot.
- cause: surcharge de WIP au lieu d’un flux terminé.
- action: garder A1+A2 en IN_SPRINT, forcer C1 en READY jusqu’au premier PASS livré et vérifié.
- effort: S
- impact: Élevé (hausse probabilité de clôture intra-sprint).
- risque: Faible (ralentit temporairement C1).
- rollback: lever la contrainte après 48h si capacité réellement sous-utilisée.
- owner_role: product_owner

4) Auto-throttle cron + garde anti-bruit NO_DELTA
- problème: pics rate-limit + bruit historique via runs/commits sans valeur.
- cause: cadence fixe et absence de gate no-op robuste.
- action: backoff exponentiel avec jitter sur rate-limit + skip persistance/commit si hash contenu inchangé (`NO_DELTA`).
- effort: M
- impact: Moyen/Élevé (stabilité quotas + meilleure lisibilité opérationnelle).
- risque: Faible/Moyen (latence plus élevée sur signaux non urgents).
- rollback: retour à fréquence fixe.
- owner_role: manager

5) Prompt library versionnée + budgets par rôle
- problème: warnings `too_long` et reformulations augmentent le cycle-time.
- cause: prompts non versionnés, contraintes de longueur non uniformes.
- action: versionner les prompts (planner/dev/tester/qa), définir budgets par rôle + template de sortie court obligatoire.
- effort: S
- impact: Moyen/Élevé (meilleur signal/bruit, coût et latence réduits).
- risque: Moyen (perte de contexte si budgets trop agressifs).
- rollback: +30% de budget par rôle et fallback template long.
- owner_role: architect

Priorités proposées pour le prochain daily scrum (Top 3)
1. Exécuter **immédiatement** un Batch-01 focalisé A1 et obtenir l’artefact `batch-01-<timestamp>.md` avec `VERDICT: PASS`.
2. Activer la gate `proof-completeness` (warn-only si besoin ce jour) pour empêcher toute transition sans preuve exploitable.
3. Tenir WIP P0=2 (A1/A2) jusqu’au premier DONE validé, puis seulement rouvrir C1.
