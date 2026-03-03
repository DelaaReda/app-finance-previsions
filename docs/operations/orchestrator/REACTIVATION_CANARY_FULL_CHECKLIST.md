# Reactivation Checklist (Canary -> Full)

Updated: 2026-03-02
Goal: réactiver sans réintroduire les blocages historiques.

## A. Pre-check (obligatoire)

- [ ] Crontab nettoyée des jobs legacy concurrents.
- [ ] Jobs canary ciblés uniquement (planner/backend au départ).
- [ ] Stale locks supprimés.
- [ ] Endpoint core accessibles.
- [ ] Charge machine stable.
- [ ] Dispatch cards prêtes pour le lot en tête.

Si un item échoue: `NO-START`.

## B. Canary phase

Rôles actifs:
- planner
- backend_engineer

Checks minimum (2 cycles successifs):
- [ ] contrat parser stable
- [ ] aucune boucle BLOCKER identique sans workaround
- [ ] preuve concrète produite sur batch en cours

Escalade immédiate si:
- rate limit en rafale
- load average explose
- erreurs contract_guard répétées

## C. Extended canary

Ajouter:
- frontend_engineer
- qa

Checks:
- [ ] clickpath valide
- [ ] preuves API/UI cohérentes
- [ ] mode dégradé visible en UI

## D. Full activation

Ajouter:
- data_analyst
- infra_engineer

Checks:
- [ ] fraîcheur et ingestion monitorées
- [ ] aucun blocker P0 non traité
- [ ] gate batch courant publiable

## E. Stop / rollback conditions

Rollback immédiat vers canary si:
- `signal_unparseable` répété,
- latence copilot hors seuil durable,
- saturation CPU ou runtime instable.

Rollback immédiat vers pause si:
- impossible de produire evidence nouvelle sur 2 cycles.

## F. Post-reactivation control (J+1)

- [ ] audit blockers par rôle
- [ ] audit token burn par rôle
- [ ] ajustement cadence cron par rôle
- [ ] plan de correction validé pour anomalies restantes
