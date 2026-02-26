# AGENT_WORKFLOW.md

## Dev Mode (Default)
Objectif: travailler "comme un dev exemplaire", avec un flux court, vérifiable et reproductible.

Références:
- `docs/ops/ENGINEERING_PLAYBOOK.md` = règles de gouvernance (4 gates).
- `docs/ops/API_ENDPOINT_BEST_PRACTICES.md` = référence exemple endpoint/API (contrat, cache, fallback, tests).
- Ce fichier = exécution quotidienne concrète.

## Definition of Ready (DoR)
Un ticket est prêt uniquement si:
- objectif unique et concret;
- scope IN/OUT explicite;
- critères d'acceptation testables;
- fichiers cibles identifiés;
- commandes de validation définies;
- risque principal + rollback rapide décrits.

## Definition of Done (DoD)
Une tâche est DONE seulement si:
- delta minimal livré (code/doc);
- tests/validations exécutés;
- preuve publiée (commandes + verdicts);
- impact utilisateur/produit décrit;
- rollback simple possible;
- limites connues explicitées;
- `VERDICT: PASS` ou `VERDICT: BLOCKED` explicite.

## Cycle De Livraison (Obligatoire)
1. Clarifier le ticket en une phrase + hypothèses explicites.
2. Découper en micro-scope livrable (2-4h max).
3. Exécuter les commandes via `scripts/exec_safe.sh` (safety gate).
4. Implémenter le plus petit delta qui satisfait les critères.
5. Lancer validations ciblées puis gate de régression adaptée.
6. Faire auto-review du diff (risques, régressions, oubli de tests).
7. Publier un rapport de preuve compact et actionnable.
8. Si blocage: remonter immédiatement commande qui échoue + cause + next action unique.

## Team Roles (Lean Solo Product)
1. Product Owner (human + orchestrator)
2. Architect/Tech Lead
3. Backend Engineer
4. Frontend Engineer
5. QA Pragmatique
6. Security Analyst
7. Codex Reviewer (independent)

Règle: moins de rôles, mieux gouvernés, plutôt que beaucoup de rôles flous.

## Ticket Template (Mandatory)
### Ticket ID
### Contexte
### Objectif
### Scope IN
### Scope OUT
### Fichiers ciblés
### Critères d'acceptation (testables)
### Commandes de validation
### Risques
### Rollback

## Agent Response Template (Mandatory)
- `STATUS`: IN_PROGRESS | PASS | BLOCKED
- `DELTA`: changements concrets
- `EVIDENCE`: commandes + résultats
- `RISKS`: risques restants
- `NEXT`: prochaine action
- `VERDICT`: PASS | BLOCKED
- `BLOCKER_ID`: `<id|NONE>`
- `NEXT_ACTION_UNIQUE`: une seule action prioritaire

## Execution Rules
- WIP max: 2 tickets.
- Taille ticket cible: 2-4h.
- Si >4h: split obligatoire.
- Pas de refacto large sans ticket dédié.
- Pas de suppression destructrice; préférer archivage contrôlé.
- Pas de "DONE" sans preuve exécutable.

## Golden Path (Backend, obligatoire)
1. Lire le ticket + identifier un scope minimal livrable en une passe.
2. Modifier uniquement les fichiers nécessaires.
3. Exécuter la gate locale:
   - `scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "./scripts/backend_regression_gate.sh --no-live"`
4. Si backend local démarré, exécuter aussi:
   - `scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "./scripts/backend_regression_gate.sh"`
5. Reporter la preuve avec commandes, verdict, risques, rollback.

## Escalation Rules
- Si commande bloquée/failed: ne pas masquer l'erreur.
- Remonter exactement:
  - commande;
  - sortie d'erreur utile;
  - impact;
  - proposition de contournement minimale.
- Si dépendance externe manque: fournir fallback local temporaire + dette explicite.

## Git Guardrails (Mandatory)
- Installer hooks: `./scripts/install-git-hooks.sh`
- `pre-commit`: bloque marqueurs WIP/TODO/FIXME/debug, check syntaxe py/sh, protège legacy
- `commit-msg`: format explicite `type(scope): summary`
- `pre-push`: bloque push sur main/master, exige workspace propre + checks minimaux
- Bypass d'urgence: `BYPASS_GUARDS=1 ...` (exception, doit être justifié)
