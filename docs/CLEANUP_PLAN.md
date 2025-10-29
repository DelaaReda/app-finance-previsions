# 🧹 Plan de Nettoyage Codebase — App Finance Prévisions

**Date Analyse**: 2025-10-29
**Analyste**: Claude Code Architect (Sonnet 4.5)
**Objectif**: Simplifier l'arborescence, éliminer redondances, faciliter navigation

---

## 📊 Résumé Exécutif

**Problèmes identifiés**:
- 🔴 **Dual UI Systems**: Streamlit (legacy) + Dash (current) = ~45 fichiers dupliqués
- 🟡 **Tests dispersés**: 30 tests dans 5 dossiers différents, duplications détectées
- 🟡 **Documentation bloat**: 185 fichiers dont 35 stubs < 100 bytes
- 🔴 **Legacy artifacts**: 1.5 MB de fichiers obsolètes (artifacts_phase1, old-context/chat.md)
- 🟡 **13 test runners**: Scripts debug one-off jamais nettoyés

**Gains attendus**:
- ✅ Suppression **100-120 fichiers** (~2-3 MB)
- ✅ Réduction **4,000-5,000 lignes** de code
- ✅ Structure **50% plus claire**
- ✅ Temps build/test **-30%**

---

## 🎯 Actions Immédiates (Priorité Haute, 0 Risque)

### Action 1: Supprimer Old Context (522 KB)
**Fichiers**:
```bash
rm -rf docs/old-context/chat.md
```

**Justification**:
- 522 KB, 8,546 lignes
- Déjà `.gitignored` (ligne 64)
- Contient historique chat obsolète + configs sensibles

**Impact**: ✅ Aucun (déjà gitignored)
**Gains**: 522 KB

---

### Action 2: Supprimer Legacy Artifacts Phase 1 (884 KB)
**Fichiers**:
```bash
rm -rf artifacts_phase1/
```

**Contenu**:
- `NGD.TO/` (37 fichiers)
- `AEM.TO/` (37 fichiers)
- Caches: `peers_cache_firecrawl.json`, `web_cache.json`, `search_ddg_*.json`

**Justification**:
- 884 KB d'artifacts "phase 1" superseded
- Déjà `.gitignored` (ligne 21)
- Jamais référencé dans code actuel

**Impact**: ✅ Aucun
**Gains**: 884 KB

---

### Action 3: Supprimer Tests E2E Redondants
**Fichiers à supprimer**:
```bash
rm tests/e2e/test_backtests_e2e.py
rm tests/e2e/test_evaluation_e2e.py
rm tests/test_pages.py
```

**Justification**:
| Fichier | Redondance | Test Équivalent |
|---------|-----------|-----------------|
| `test_backtests_e2e.py` | Teste `#backtests-topn-curve` | `test_backtests_page.py` (unit) |
| `test_evaluation_e2e.py` | Teste `#evaluation-table` | `test_evaluation_page.py` (unit) |
| `test_pages.py` | Teste layout news/deep_dive | `test_all_pages_e2e.py` (smoke) |

**Impact**: ⚠️ Vérifier que tests unit couvrent fonctionnalité
**Gains**: 3 fichiers, ~150 lignes

---

### Action 4: Cleanup Test Runners Obsolètes
**Fichiers à déplacer vers `scripts/debug_archive/`**:
```bash
mkdir -p scripts/debug_archive
mv src/runners/test_*.py scripts/debug_archive/
# Garder uniquement: sanity_runner.py, test_import_validation.py (si utilisés en CI)
```

**Fichiers concernés** (13 fichiers, tous datés Sep 15-26):
- `test.py`, `test_comprehensive.py`, `test_app_integration.py`
- `test_econ_functions.py`, `test_econ_llm_agent.py`
- `test_fred_*.py` (5 fichiers)
- `test_import_validation.py`, `test_macro_fix.py`
- `test_market_data.py`, `test_phase1_live.py`, `test_phase2_technical.py`

**Justification**:
- Aucun modifié en octobre (1+ mois)
- Scripts debug one-off
- Pas importés ailleurs (vérifié grep)

**Impact**: ⚠️ Vérifier si `sanity_runner.py` utilisé en CI
**Gains**: 9-11 fichiers, ~500 lignes

---

### Action 5: Réorganiser Sprint Reports
**Fichiers à déplacer**:
```bash
mkdir -p docs/sprints/archive
mv PROGRESS_SPRINT5.md docs/sprints/archive/
mv SPRINT_SONNET_2_DELIVERY.md docs/sprints/archive/
mv SPRINT_SONNET_2_REPORT.md docs/sprints/archive/
mv MIGRATION_SPRINT11.md docs/sprints/archive/
mv ARCHITECTURE_DELIVERY_SUMMARY.md docs/architecture/
mv STREAMLIT.md docs/architecture/
```

**Fichiers root à garder**:
- `README.md` (guide principal)
- `PROGRESS.md` (status actuel)
- `AGENTS.md` (si existe, doc agents)
- `QA_REPORT.md` (status QA actuel)

**Justification**:
- 6 fichiers sprint/delivery à la racine → confusion
- Regrouper historique sprints dans dossier dédié

**Impact**: ✅ Aucun (déplacement)
**Gains**: Root directory -50% files

---

## 📋 Total Actions Immédiates

**Commandes à exécuter** (copier-coller):
```bash
# 1. Supprimer old context
rm -rf docs/old-context/chat.md

# 2. Supprimer legacy artifacts
rm -rf artifacts_phase1/

# 3. Supprimer tests redondants
rm tests/e2e/test_backtests_e2e.py
rm tests/e2e/test_evaluation_e2e.py
rm tests/test_pages.py

# 4. Archiver test runners obsolètes
mkdir -p scripts/debug_archive
mv src/runners/test_*.py scripts/debug_archive/ 2>/dev/null || true
# Restaurer ceux utilisés en CI (si nécessaire):
# git checkout src/runners/test_import_validation.py

# 5. Réorganiser sprint reports
mkdir -p docs/sprints/archive
mv PROGRESS_SPRINT5.md docs/sprints/archive/
mv SPRINT_SONNET_2_DELIVERY.md docs/sprints/archive/
mv SPRINT_SONNET_2_REPORT.md docs/sprints/archive/
mv MIGRATION_SPRINT11.md docs/sprints/archive/
mv ARCHITECTURE_DELIVERY_SUMMARY.md docs/architecture/
mv STREAMLIT.md docs/architecture/

# 6. Commit cleanup
git add -A
git commit -m "chore(cleanup): remove legacy artifacts, redundant tests, and reorganize docs

- Remove old-context/chat.md (522KB obsolete chat history)
- Remove artifacts_phase1/ (884KB legacy phase 1 data)
- Remove 3 redundant e2e tests (backtests, evaluation, pages)
- Archive 9-11 obsolete test runners to scripts/debug_archive/
- Reorganize sprint reports to docs/sprints/archive/
- Move architecture docs from root to docs/architecture/

Total cleanup: ~1.5MB, 15+ files removed, root directory simplified.
"
```

**Gains totaux Actions Immédiates**:
- **Fichiers**: ~18 supprimés, ~6 déplacés
- **Taille**: ~1.5 MB
- **Lignes**: ~650 lignes code
- **Risque**: ✅ Très faible (fichiers obsolètes/redondants)

---

## 🔄 Actions Court Terme (1-2 Sprints)

### Action 6: Consolider Documentation UI
**Objectif**: 1 seul guide migration UI au lieu de 4 documents

**Fichiers à fusionner dans `docs/architecture/ui-migration-guide.md`**:
- `docs/architecture/dash_migration.md` (4.7KB)
- `docs/architecture/dash_overview.md` (2.7KB)
- `docs/architecture/STREAMLIT.md` (déplacé à l'action 5)
- `docs/ui/ui_audit.md` (2.6KB)

**Structure proposée `ui-migration-guide.md`**:
```markdown
# Guide Migration UI — Streamlit → Dash

## 1. État Actuel
- Dash = UI principale (production)
- Streamlit = legacy (maintenance ponctuelle uniquement)

## 2. Timeline Migration
- Q4 2024: Feature freeze Streamlit
- Q1 2025: Deprecation warnings ajoutées
- Q2 2025: Suppression Streamlit

## 3. Comparaison Architectures
(Contenu de dash_overview.md)

## 4. Plan Migration Détaillé
(Contenu de dash_migration.md)

## 5. Audit UI
(Contenu de ui_audit.md)
```

**Impact**: ⚠️ Vérifier pas de liens externes vers fichiers supprimés
**Gains**: 4 → 1 fichier, clarté +100%

---

### Action 7: Réorganiser API Docs (138 → ~80 fichiers)
**Problème**: 138 fichiers API dont 35 stubs < 100 bytes

**Plan**:
1. **Supprimer docs Streamlit pages** (src/apps/pages/):
   ```bash
   rm docs/api/src__apps__pages__*.py.md
   ```
   ➜ -28 fichiers

2. **Supprimer docs test runners**:
   ```bash
   rm docs/api/src__runners__test*.py.md
   ```
   ➜ -13 fichiers

3. **Régénérer API docs** avec filtres:
   - Exclure fichiers < 10 lignes
   - Exclure tests/runners
   - Grouper par module

4. **Organiser hiérarchiquement**:
   ```
   docs/api/
   ├── README.md
   ├── core/
   ├── agents/
   ├── analytics/
   ├── dash_app/
   └── tools/
   ```

**Impact**: ⚠️ Régénération requise (Make target `api-docs-generate`)
**Gains**: 138 → ~80 fichiers (-42%)

---

### Action 8: Standardiser Structure Tests
**Objectif**: 1 dossier par type de test

**Réorganisation proposée**:
```
tests/
├── unit/               # Tests unitaires (logique isolée)
│   ├── test_alerts_parsing.py
│   ├── test_deep_dive_logic.py
│   ├── test_settings_watchlist.py
│   └── test_parquet_io.py (déplacé depuis tests/tools/)
│
├── integration/        # Tests integration (data sources)
│   ├── test_freshness_and_sources.py
│   ├── test_macro_sources.py
│   ├── test_stock_data.py
│   ├── test_alerts_sources.py
│   └── test_settings_io.py
│
├── pages/              # Tests pages Dash (NOUVEAU dossier)
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
│   # (déplacés depuis tests/ root)
│
├── e2e/                # Tests E2E (smoke tests)
│   ├── test_all_pages_e2e.py (garde heuristics)
│   └── test_routes.py (déplacé depuis tests/ui/)
│
└── llm/                # Tests LLM (garde séparé)
    └── test_llm_summary.py
```

**Commandes**:
```bash
# Créer structure
mkdir -p tests/pages

# Déplacer tests pages
mv tests/test_*_page.py tests/pages/

# Déplacer test routes
mv tests/ui/test_routes.py tests/e2e/

# Déplacer test parquet_io
mv tests/tools/test_parquet_io.py tests/unit/

# Supprimer dossiers vides
rmdir tests/ui tests/tools
```

**Impact**: ⚠️ Mettre à jour imports si paths absolus
**Gains**: 5 → 4 dossiers, structure +100% claire

---

### Action 9: Ajouter Deprecation Warnings Streamlit
**Objectif**: Préparer suppression Q1 2026

**Modifications `src/apps/app.py`**:
```python
import streamlit as st
import warnings

# En haut du fichier
warnings.warn(
    "⚠️ DEPRECATION: Streamlit UI is deprecated and will be removed in Q1 2026. "
    "Please migrate to Dash UI (port 8050). "
    "See docs/architecture/ui-migration-guide.md for migration path.",
    DeprecationWarning,
    stacklevel=2
)

st.warning("""
⚠️ **AVERTISSEMENT**: Cette interface Streamlit est obsolète.

**Migration requise**: Veuillez utiliser l'interface Dash (port 8050).

**Timeline**:
- Q4 2024: Feature freeze (aucune nouvelle fonctionnalité)
- Q1 2025: Deprecation warnings (actuel)
- Q2 2025: Suppression complète

**Guide migration**: `docs/architecture/ui-migration-guide.md`
""")
```

**Impact**: ⚠️ Utilisateurs Streamlit voient warning
**Gains**: Communication claire timeline

---

## 🚀 Actions Long Terme (Q1 2026)

### Action 10: Supprimer Streamlit Complètement
**Date cible**: Mars 2026 (après 3 mois deprecation)

**Fichiers à supprimer**:
```bash
# Supprimer pages Streamlit (28 fichiers)
rm -rf src/apps/pages/

# Supprimer Streamlit skeleton (17 fichiers)
rm -rf src/apps/streamlit/

# Supprimer apps support
rm src/apps/agent_app.py
rm src/apps/forecast_app.py
rm src/apps/macro_sector_app.py
rm src/apps/stock_analysis_app.py

# Garder seulement stub avec redirect
cat > src/apps/app.py << 'EOF'
"""
DEPRECATED: Streamlit UI removed in Q1 2026.
Please use Dash UI: http://localhost:8050
"""
import sys
print("❌ Streamlit UI has been removed.")
print("✅ Please use Dash UI: http://localhost:8050")
print("📖 Migration guide: docs/architecture/ui-migration-guide.md")
sys.exit(1)
EOF
```

**Impact**: 🔴 Breaking change (mais annoncé 3 mois avant)
**Gains**: ~45 fichiers, ~3,500 lignes

---

## 📊 Métriques Totales Cleanup

### Gains Immédiats (Actions 1-5)
- **Fichiers supprimés**: 18
- **Fichiers déplacés**: 6
- **Taille libérée**: ~1.5 MB
- **Lignes code**: ~650
- **Risque**: ✅ Très faible
- **Durée**: 30 min

### Gains Court Terme (Actions 6-9)
- **Fichiers supprimés**: ~50
- **Fichiers réorganisés**: ~20
- **Docs consolidés**: 4 → 1 guide UI
- **API docs**: 138 → ~80
- **Risque**: ⚠️ Moyen (tests à vérifier)
- **Durée**: 4-8 heures (1 sprint)

### Gains Long Terme (Action 10)
- **Fichiers supprimés**: ~45
- **Lignes code**: ~3,500
- **Risque**: 🔴 Breaking change (annoncé)
- **Durée**: 2-4 heures

### **TOTAL**
| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| Fichiers | ~500 | ~387 | **-113 (-23%)** |
| Taille code | ~15 MB | ~12 MB | **-3 MB (-20%)** |
| Lignes code | ~20,000 | ~16,000 | **-4,000 (-20%)** |
| Dossiers root MD | 12 | 4 | **-8 (-67%)** |
| Tests fichiers | 30 | ~20 | **-10 (-33%)** |
| Docs fichiers | 185 | ~110 | **-75 (-41%)** |

---

## ✅ Checklist Exécution

### Phase 1: Actions Immédiates (Aujourd'hui)
- [ ] Backup: `git branch cleanup-backup-$(date +%Y%m%d)`
- [ ] Action 1: Supprimer old-context/chat.md
- [ ] Action 2: Supprimer artifacts_phase1/
- [ ] Action 3: Supprimer tests redondants (3 fichiers)
- [ ] Action 4: Archiver test runners (9-11 fichiers)
- [ ] Action 5: Réorganiser sprint reports (6 fichiers)
- [ ] Commit: "chore(cleanup): phase 1 immediate cleanup"
- [ ] Push: `git push origin main`

### Phase 2: Actions Court Terme (Sprint +1)
- [ ] Action 6: Consolider docs UI (4 → 1)
- [ ] Action 7: Réorganiser API docs (138 → 80)
- [ ] Action 8: Standardiser structure tests
- [ ] Action 9: Ajouter deprecation warnings Streamlit
- [ ] Tests: Vérifier tous tests passent après réorg
- [ ] Commit: "chore(cleanup): phase 2 reorganization"

### Phase 3: Actions Long Terme (Q1 2026)
- [ ] Annonce: Email/Slack 3 mois avant suppression
- [ ] Vérification: Aucun usage Streamlit (logs analytics)
- [ ] Action 10: Supprimer Streamlit complètement
- [ ] Tests: Vérifier build après suppression
- [ ] Commit: "feat(breaking): remove deprecated Streamlit UI"
- [ ] Release notes: Documenter breaking change

---

## 🔍 Validation Post-Cleanup

**Commandes de vérification**:
```bash
# 1. Tests passent
make test

# 2. Dash démarre
make dash-start
# Ouvrir http://localhost:8050 → vérifier pages

# 3. Imports OK
python -c "import src.dash_app.app; print('✅ Dash import OK')"

# 4. Docs accessibles
ls docs/architecture/ui-migration-guide.md
ls docs/sprints/archive/

# 5. Taille projet
du -sh .
# Avant: ~15 MB
# Après: ~12 MB

# 6. Compte fichiers
find . -name "*.py" -o -name "*.md" | grep -v ".venv" | grep -v ".git" | wc -l
# Avant: ~500
# Après: ~387
```

---

## 📚 Références

- **Analyse complète**: `docs/CLEANUP_ANALYSIS_DETAILED.md`
- **Fichiers à supprimer**: `docs/CLEANUP_FILES_TO_DELETE.md`
- **Guide migration UI**: `docs/architecture/ui-migration-guide.md` (à créer)
- **Engineering rules**: `docs/dev/engineering_rules.md`

---

**Version**: 1.0
**Prochaine revue**: Fin Sprint +1 (après actions court terme)
