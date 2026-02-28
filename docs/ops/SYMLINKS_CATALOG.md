# Catalogue des symlinks – Référence agents

**Date:** 2026-02-28  
**Objectif:** Documenter les symlinks pour éviter confusion et maintenir un chemin canonique dans le code/docs.

---

## Règle générale

**Chemin canonique** = utiliser celui-ci dans tout nouveau code et documentation.  
**Alias** = symlink conservé pour compatibilité, à ne pas privilégier pour les nouvelles références.

---

## Symlinks racine

| Alias (symlink) | Cible canonique | Usage |
|-----------------|-----------------|-------|
| `data` | `apps/api/runtime/data` | Données runtime (forecasts, news, etc.) |
| `cache` | `apps/api/runtime/cache` | Cache runtime |
| `runtime` | `apps/api/runtime` | Répertoire runtime global |

**Convention:** Dans les scripts et la doc, préférer `apps/api/runtime/` et sous-chemins.

---

## Mémoire / planning

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `memory/today.md` | `memory/YYYY-MM-DD.md` | Lien vers mémoire du jour |
| `memory/yesterday.md` | `memory/YYYY-MM-DD.md` | Lien vers mémoire veille |
| `docs/planning/*` | `docs/product/planning/*` | Accès court au planning |

---

## Gates et preuves

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `finance-app/openclaw-gates` | `evidence/gates/openclaw-gates` | Artefacts batch (batch-01, batch-02, etc.) |

**Canonique:** `evidence/gates/openclaw-gates/` — scripts (`preflight_dispatch`, `run_delivery_gate`) et nouvelle doc doivent l’utiliser. L’alias `finance-app/` reste pour compatibilité avec `tasks.md`, `priority-queue.json`, etc.

---

## Backend (apps/api/src)

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `apps/api/src/data` | `../runtime/data` | Données vues depuis le code |
| `apps/api/src/cache` | `../runtime/cache` | Cache vu depuis le code |
| `apps/api/src/tests` | `../tests` | Découverte pytest (tests dans `domains/*/tests/`) |
| `apps/api/src/.venv` | `../../../.venv` | Environnement virtuel |
| `apps/api/src/legacy-archive` | `archive/legacy/...` | Archive legacy |

---

## Documentation

| Alias | Cible canonique | Usage |
|-------|-----------------|-------|
| `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml` | `docs/ops/ops/ORCHESTRATION_COORDINATION_SPEC.yaml` | Spec orchestration (réf. docs) |

## Scripts

De nombreux scripts dans `scripts/` sont des symlinks vers `platform/policies/` ou `platform/automation/`.  
**Canonique:** le fichier se trouve dans `platform/` ; `scripts/` expose un alias pour les commandes courtes.

---

## Risques et bonnes pratiques

1. **Ne pas créer de symlink** sans le documenter ici.
2. **Préférer le chemin canonique** dans tout nouveau code ou documentation.
3. En cas de **renommage ou déplacement** de la cible, mettre à jour ce catalogue et vérifier les liens.
4. Les **chemins relatifs** dans les symlinks peuvent casser si la structure du projet change.

---

*Voir aussi: `docs/ops/AGENTS_READY.md`, `docs/ops/REMPISE_ORDRE_POST_MIGRATION.md`*
