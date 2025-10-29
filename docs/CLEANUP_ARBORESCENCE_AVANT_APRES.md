# 📂 Arborescence Avant/Après Cleanup

**Date**: 2025-10-29
**Objectif**: Visualiser simplification structure projet

---

## 🔴 AVANT Cleanup (État Actuel)

### Structure Racine (12+ fichiers MD)
```
/
├── README.md ✅ (garder)
├── PROGRESS.md ✅ (garder)
├── AGENTS.md ✅ (garder)
├── QA_REPORT.md ✅ (garder)
├── PROGRESS_SPRINT5.md ❌ (déplacer)
├── SPRINT_SONNET_2_DELIVERY.md ❌ (déplacer)
├── SPRINT_SONNET_2_REPORT.md ❌ (déplacer)
├── MIGRATION_SPRINT11.md ❌ (déplacer)
├── ARCHITECTURE_DELIVERY_SUMMARY.md ❌ (déplacer)
├── STREAMLIT.md ❌ (déplacer)
├── WEB_EVAL_SETUP_REPORT.md ⚠️ (vérifier)
├── PARTITIONS_FRESHNESS.md ✅ (garder, doc importante)
└── ... (autres)
```

**Problème**: 12+ fichiers → confusion "où est la doc?"

---

### Dossier `docs/` (15 sous-dossiers, 185 fichiers)
```
docs/
├── agents/ (2 fichiers) ✅
├── api/ (138 fichiers) ❌ 35 stubs vides, 28 Streamlit, 13 test runners
│   ├── README.md ✅
│   ├── src__apps__pages__*.py.md ❌ (28 fichiers Streamlit)
│   ├── src__runners__test*.py.md ❌ (13 fichiers test runners)
│   └── ... (97 fichiers à garder)
├── architecture/ (13 fichiers) ⚠️ Redondances
│   ├── adr/ (3 ADR) ✅
│   ├── impl/ (1 plan) ✅
│   ├── dash_migration.md ❌ (fusionner)
│   ├── dash_overview.md ❌ (fusionner)
│   ├── vision.md ✅
│   └── ...
├── atlas/ (1 fichier) ⚠️
├── dev/ (4 fichiers) ✅
├── dev-junior/ (1 fichier) ✅
├── ideas/ (3 fichiers) ✅
├── implementation/ (3 specs) ✅
├── old-context/ ❌ (à supprimer)
│   └── chat.md (522 KB, 8,546 lignes) ❌
├── product/ (2 fichiers) ✅
├── qa/ (3 fichiers) ✅
├── roles/ (2 fichiers) ✅
├── runbook/ (1 fichier) ✅
├── ui/ (1 fichier) ⚠️ (fusionner dans architecture)
└── sprints/ ❌ (à créer pour archive)
```

**Problème**: 138 API docs dont 35 stubs, docs UI dispersés

---

### Dossier `tests/` (30 fichiers, 7 sous-dossiers)
```
tests/
├── test_dashboard_page.py ⚠️ (déplacer vers tests/pages/)
├── test_signals_page.py ⚠️
├── test_forecasts_page.py ⚠️
├── test_deep_dive_page.py ⚠️
├── test_backtests_page.py ⚠️
├── test_evaluation_page.py ⚠️
├── test_quality_page.py ⚠️
├── test_agents_status_page.py ⚠️
├── test_alerts_page.py ⚠️
├── test_settings_page.py ⚠️
├── test_pages.py ❌ (redondant avec test_all_pages_e2e.py)
├── test_dash_ui.py ⚠️
├── test_app_data.py ⚠️
├── test_integration_news.py ⚠️ (vieux, Sep 25)
│
├── e2e/ (4 fichiers)
│   ├── test_all_pages_e2e.py ✅ (smoke test complet)
│   ├── test_backtests_e2e.py ❌ (redondant)
│   ├── test_evaluation_e2e.py ❌ (redondant)
│   └── test_risk_regimes_e2e.py ✅
│
├── integration/ (5 fichiers) ✅
├── unit/ (3 fichiers) ✅
├── ui/ (1 fichier) ⚠️ (déplacer vers e2e/)
├── llm/ (1 fichier) ✅
└── tools/ (1 fichier) ⚠️ (déplacer vers unit/)
```

**Problème**: 10 tests pages à la racine, tests dispersés dans 7 dossiers

---

### Dossier `artifacts_phase1/` ❌ (à supprimer)
```
artifacts_phase1/
├── NGD.TO/ (37 fichiers JSON/CSV) ❌
├── AEM.TO/ (37 fichiers JSON/CSV) ❌
└── *.json (caches, 4 fichiers) ❌
```

**Problème**: 884 KB legacy, déjà gitignored, jamais utilisé

---

### Dossier `src/runners/` (15+ fichiers)
```
src/runners/
├── sanity_runner.py ✅ (si utilisé CI)
├── sanity_runner_ia_chat.py ⚠️
├── test.py ❌ (debug one-off)
├── test_app_integration.py ❌
├── test_comprehensive.py ❌
├── test_econ_functions.py ❌
├── test_econ_llm_agent.py ❌
├── test_fred_debug.py ❌
├── test_fred_env.py ❌
├── test_fred_integration.py ❌
├── test_fred_simple.py ❌
├── test_import_validation.py ✅ (si utilisé CI)
├── test_macro_fix.py ❌
├── test_market_data.py ❌
├── test_phase1_live.py ❌
└── test_phase2_technical.py ❌
```

**Problème**: 13 test runners debug jamais nettoyés (tous Sep 15-26)

---

## 🟢 APRÈS Cleanup (État Cible)

### Structure Racine (4 fichiers MD essentiels)
```
/
├── README.md ✅ Guide principal
├── PROGRESS.md ✅ Status actuel
├── AGENTS.md ✅ Doc agents
├── QA_REPORT.md ✅ Status QA
└── PARTITIONS_FRESHNESS.md ✅ Doc partitions
```

**Gains**: 12 → 5 fichiers (-58%), clarté +200%

---

### Dossier `docs/` (12 sous-dossiers, ~110 fichiers)
```
docs/
├── agents/ (2 fichiers) ✅
│   ├── README.md
│   └── AGENTS_PROMPT.md (déplacé depuis racine)
│
├── api/ (~80-90 fichiers organisés) ✅
│   ├── README.md
│   ├── core/ (config, models, market_data, io_utils)
│   ├── agents/ (equity_forecast, macro_forecast, etc.)
│   ├── analytics/ (phase1-5, ml_baseline, econ_llm)
│   ├── dash_app/ (pages, data, logic)
│   └── tools/ (parquet_io, make, git_patcher)
│
├── architecture/ (10 fichiers consolidés) ✅
│   ├── adr/ (3 ADR)
│   ├── impl/ (1 plan sprint)
│   ├── ARCHITECTURE_DELIVERY_SUMMARY.md (déplacé depuis racine)
│   ├── STREAMLIT.md (déplacé depuis racine)
│   ├── ui-migration-guide.md ✅ NOUVEAU (fusion 4 docs)
│   ├── vision.md
│   ├── c4.md
│   ├── data_flow.md
│   └── refactor_plan.md
│
├── dev/ (4 fichiers) ✅
├── dev-junior/ (1 fichier) ✅
├── ideas/ (3 fichiers) ✅
├── implementation/ (3 specs) ✅
│
├── product/ (2 fichiers) ✅
│
├── qa/ (3 fichiers) ✅
│
├── roles/ (2 fichiers) ✅
│
├── runbook/ (1 fichier) ✅
│
└── sprints/ ✅ NOUVEAU
    └── archive/
        ├── PROGRESS_SPRINT5.md
        ├── SPRINT_SONNET_2_DELIVERY.md
        ├── SPRINT_SONNET_2_REPORT.md
        └── MIGRATION_SPRINT11.md
```

**Gains**:
- API docs: 138 → ~85 fichiers (-38%)
- Docs UI: 4 → 1 guide consolidé
- Sprint reports archivés (pas à la racine)
- old-context/ supprimé (-522 KB)

---

### Dossier `tests/` (~20 fichiers, 4 sous-dossiers)
```
tests/
├── unit/ (5 fichiers) ✅
│   ├── test_alerts_parsing.py
│   ├── test_deep_dive_logic.py
│   ├── test_settings_watchlist.py
│   └── test_parquet_io.py (déplacé depuis tools/)
│
├── integration/ (5 fichiers) ✅
│   ├── test_freshness_and_sources.py
│   ├── test_macro_sources.py
│   ├── test_stock_data.py
│   ├── test_alerts_sources.py
│   └── test_settings_io.py
│
├── pages/ (10 fichiers) ✅ NOUVEAU
│   ├── test_dashboard_page.py
│   ├── test_signals_page.py
│   ├── test_forecasts_page.py
│   ├── test_deep_dive_page.py
│   ├── test_backtests_page.py
│   ├── test_evaluation_page.py
│   ├── test_quality_page.py
│   ├── test_agents_status_page.py
│   ├── test_alerts_page.py
│   └── test_settings_page.py
│
├── e2e/ (2 fichiers) ✅
│   ├── test_all_pages_e2e.py (smoke complet)
│   └── test_routes.py (déplacé depuis ui/)
│
└── llm/ (1 fichier) ✅
    └── test_llm_summary.py
```

**Gains**:
- 30 → ~23 fichiers (-23%)
- 7 → 5 dossiers (-29%)
- Structure logique: unit/integration/pages/e2e/llm
- Tests redondants supprimés (backtests_e2e, evaluation_e2e, pages.py)

---

### Dossier `scripts/` ✅ NOUVEAU
```
scripts/
├── cleanup_phase1.sh ✅ Script cleanup automatique
├── cleanup_phase2.sh ✅ (à créer Sprint +1)
└── debug_archive/ (9-11 fichiers archivés)
    ├── test.py
    ├── test_app_integration.py
    ├── test_comprehensive.py
    ├── test_econ_functions.py
    ├── test_fred_*.py (5 fichiers)
    └── ...
```

**Gains**:
- Test runners archivés (pas supprimés, au cas où)
- Scripts cleanup versionnés

---

### Dossier `src/runners/` (2-3 fichiers)
```
src/runners/
├── sanity_runner.py ✅ (si utilisé CI)
├── sanity_runner_ia_chat.py ⚠️ (vérifier utilité)
└── test_import_validation.py ✅ (si utilisé CI)
```

**Gains**: 15 → 2-3 fichiers (-80%)

---

## 📊 Comparaison Globale

### Fichiers Totaux
| Catégorie | Avant | Après | Gain |
|-----------|-------|-------|------|
| **Racine MD** | 12 | 5 | -58% |
| **docs/** | 185 | ~110 | -41% |
| **tests/** | 30 | ~23 | -23% |
| **src/runners/** | 15 | 2-3 | -80% |
| **Total fichiers .py/.md** | ~500 | ~387 | -23% |

---

### Taille Disque
| Avant | Après | Libéré |
|-------|-------|--------|
| ~15 MB | ~12 MB | **-3 MB (-20%)** |

---

### Sous-dossiers
| Dossier | Avant | Après | Gain |
|---------|-------|-------|------|
| `docs/` | 15 | 12 | -20% |
| `tests/` | 7 | 5 | -29% |
| `racine` | - | +1 (`scripts/`) | +organisation |

---

## 🎯 Bénéfices Navigation

### Avant
❌ Développeur cherche doc migration UI:
1. Racine: `STREAMLIT.md`? (parle juste status)
2. `docs/ui/ui_audit.md`? (parle audit, pas migration)
3. `docs/architecture/dash_migration.md`? (plan, mais incomplet)
4. `docs/architecture/dash_overview.md`? (overview, pas howto)
→ **4 fichiers à lire**, info fragmentée

❌ Développeur cherche test page Dashboard:
1. `tests/test_dashboard_page.py`? (racine)
2. `tests/e2e/test_*`? (pas là)
3. `tests/ui/`? (non)
→ **Dispersion**, pas de logique

---

### Après
✅ Développeur cherche doc migration UI:
1. `docs/architecture/ui-migration-guide.md`
→ **1 fichier**, tout en 1

✅ Développeur cherche test page Dashboard:
1. `tests/pages/test_dashboard_page.py`
→ **Logique claire**, tous tests pages dans `tests/pages/`

✅ Développeur veut voir historique sprint:
1. `docs/sprints/archive/`
→ **Organisation chronologique**

---

## 📋 Checklist Migration

### Phase 1: Immédiat
- [ ] Supprimer `docs/old-context/chat.md` (522 KB)
- [ ] Supprimer `artifacts_phase1/` (884 KB, 71 fichiers)
- [ ] Supprimer tests redondants (3 fichiers)
- [ ] Archiver test runners → `scripts/debug_archive/` (9-11 fichiers)
- [ ] Créer `docs/sprints/archive/` + déplacer 4 rapports sprint
- [ ] Déplacer 2 docs archi (ARCHITECTURE_DELIVERY_SUMMARY, STREAMLIT)

**Résultat**: Racine -50% fichiers, -1.5 MB

---

### Phase 2: Court Terme (Sprint +1)
- [ ] Fusionner 4 docs UI → `docs/architecture/ui-migration-guide.md`
- [ ] Supprimer 28 API docs Streamlit pages
- [ ] Supprimer 13 API docs test runners
- [ ] Régénérer API docs (exclure stubs < 100 bytes)
- [ ] Organiser API docs par module (core/, agents/, analytics/, etc.)
- [ ] Créer `tests/pages/` + déplacer 10 tests
- [ ] Déplacer `tests/ui/test_routes.py` → `tests/e2e/`
- [ ] Déplacer `tests/tools/test_parquet_io.py` → `tests/unit/`

**Résultat**: tests/ -7 fichiers, API docs -50 fichiers, structure +100% claire

---

### Phase 3: Long Terme (Q1 2026)
- [ ] Supprimer `src/apps/pages/` (28 fichiers Streamlit)
- [ ] Supprimer `src/apps/streamlit/` (17 fichiers skeleton)
- [ ] Supprimer 4 apps support Streamlit
- [ ] Remplacer `src/apps/app.py` par stub deprecation

**Résultat**: -50 fichiers, -3,500 lignes code

---

## 🚀 Impact Onboarding

### Avant (Nouveau Dev)
1. Clone repo
2. Voit 12 fichiers MD racine → confusion "lequel lire?"
3. Ouvre `docs/` → 15 sous-dossiers, 185 fichiers → overwhelmed
4. Cherche tests Dashboard → trouve `tests/test_dashboard_page.py` (racine), pas `tests/e2e/`, pas `tests/pages/`
5. Cherche doc UI → trouve 4 fichiers différents, info fragmentée
→ **Temps onboarding: 2-3 heures**

---

### Après (Nouveau Dev)
1. Clone repo
2. Voit 5 fichiers MD racine → lit `README.md` (clair)
3. Ouvre `docs/` → structure logique (architecture/, sprints/archive/, implementation/)
4. Cherche tests Dashboard → `tests/pages/test_dashboard_page.py` (logique)
5. Cherche doc UI → `docs/architecture/ui-migration-guide.md` (1 fichier)
→ **Temps onboarding: 30-45 min** (-75%)

---

## 📚 Références

- **Plan cleanup**: `docs/CLEANUP_PLAN.md`
- **Fichiers à supprimer**: `docs/CLEANUP_FILES_TO_DELETE.md`
- **Script cleanup Phase 1**: `scripts/cleanup_phase1.sh`

---

**Version**: 1.0
**Dernière mise à jour**: 2025-10-29
