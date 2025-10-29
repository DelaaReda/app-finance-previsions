# 🗑️ Fichiers à Supprimer — Liste Exacte

**Date**: 2025-10-29
**Objectif**: Liste précise de tous les fichiers à supprimer/déplacer

---

## 🔴 PHASE 1: Suppression Immédiate (0 Risque)

### 1.1 Old Context (522 KB)
```bash
# Fichier unique
docs/old-context/chat.md
```

**Total**: 1 fichier, 522 KB

---

### 1.2 Artifacts Phase 1 (884 KB)
```bash
# Dossier complet
artifacts_phase1/NGD.TO/
artifacts_phase1/AEM.TO/
artifacts_phase1/*.json
```

**Liste détaillée**:
```
artifacts_phase1/NGD.TO/summary.json
artifacts_phase1/NGD.TO/p1_build_peer_set.json
artifacts_phase1/NGD.TO/p1_load_prices.json
artifacts_phase1/NGD.TO/p1_load_info.json
artifacts_phase1/NGD.TO/yf_fast_info.json
artifacts_phase1/NGD.TO/p1_compute_company_multiples.json
artifacts_phase1/NGD.TO/p1_estimate_beta.json
artifacts_phase1/NGD.TO/p1_dcf_simplified.json
artifacts_phase1/NGD.TO/p1_compute_health_ratios.json
artifacts_phase1/NGD.TO/p1_fetch_peer_multiples.json
artifacts_phase1/NGD.TO/p1_build_fundamental_view.json
artifacts_phase1/NGD.TO/p1_load_fundamentals.json
artifacts_phase1/AEM.TO/summary.json
artifacts_phase1/AEM.TO/p1_build_peer_set.json
artifacts_phase1/AEM.TO/p1_load_prices.json
artifacts_phase1/AEM.TO/p1_load_info.json
artifacts_phase1/AEM.TO/yf_fast_info.json
artifacts_phase1/AEM.TO/p1_compute_company_multiples.json
artifacts_phase1/AEM.TO/p1_estimate_beta.json
artifacts_phase1/AEM.TO/p1_dcf_simplified.json
artifacts_phase1/AEM.TO/p1_compute_health_ratios.json
artifacts_phase1/AEM.TO/p1_fetch_peer_multiples.json
artifacts_phase1/AEM.TO/p1_build_fundamental_view.json
artifacts_phase1/AEM.TO/p1_load_fundamentals.json
artifacts_phase1/search_cache.json
artifacts_phase1/search_ddg_1757611641.json
artifacts_phase1/web_cache.json
artifacts_phase1/scrape_cache.json
artifacts_phase1/peers_cache_firecrawl.json
```

**Total**: 71 fichiers, 884 KB

---

### 1.3 Tests Redondants (3 fichiers)
```bash
tests/e2e/test_backtests_e2e.py
tests/e2e/test_evaluation_e2e.py
tests/test_pages.py
```

**Raison suppression**:
- `test_backtests_e2e.py`: Duplique `test_backtests_page.py`
- `test_evaluation_e2e.py`: Duplique `test_evaluation_page.py`
- `test_pages.py`: Superseded par `test_all_pages_e2e.py`

**Total**: 3 fichiers, ~150 lignes

---

### 1.4 Test Runners Obsolètes (11 fichiers)
**À déplacer vers `scripts/debug_archive/`** (pas suppression immédiate):
```bash
src/runners/test.py
src/runners/test_app_integration.py
src/runners/test_comprehensive.py
src/runners/test_econ_functions.py
src/runners/test_econ_llm_agent.py
src/runners/test_fred_debug.py
src/runners/test_fred_env.py
src/runners/test_fred_integration.py
src/runners/test_fred_simple.py
src/runners/test_macro_fix.py
src/runners/test_market_data.py
src/runners/test_phase1_live.py
src/runners/test_phase2_technical.py
```

**Exceptions** (à garder si utilisés en CI):
```bash
# Vérifier avant de déplacer:
src/runners/sanity_runner.py
src/runners/test_import_validation.py
```

**Total**: 11-13 fichiers, ~500 lignes

---

### 1.5 Sprint Reports à Déplacer (6 fichiers)
**Déplacer de racine vers `docs/sprints/archive/`**:
```bash
PROGRESS_SPRINT5.md
SPRINT_SONNET_2_DELIVERY.md
SPRINT_SONNET_2_REPORT.md
MIGRATION_SPRINT11.md
```

**Déplacer vers `docs/architecture/`**:
```bash
ARCHITECTURE_DELIVERY_SUMMARY.md
STREAMLIT.md
```

**Total**: 6 fichiers déplacés (pas supprimés)

---

## 🟡 PHASE 2: Court Terme (Sprint +1)

### 2.1 API Docs Streamlit Pages (28 fichiers)
**À supprimer après vérification pas de liens**:
```bash
docs/api/src__apps__pages__00_Home.py.md
docs/api/src__apps__pages__1_Dashboard.py.md
docs/api/src__apps__pages__2_News.py.md
docs/api/src__apps__pages__3_Deep_Dive.py.md
docs/api/src__apps__pages__4_Forecasts.py.md
docs/api/src__apps__pages__6_Backtests.py.md
docs/api/src__apps__pages__7_Reports.py.md
docs/api/src__apps__pages__8_Evaluation.py.md
docs/api/src__apps__pages__11_Quality.py.md
docs/api/src__apps__pages__12_Agents.py.md
docs/api/src__apps__pages__13_LLM_Models.py.md
docs/api/src__apps__pages__14_Regimes.py.md
docs/api/src__apps__pages__16_Portfolio.py.md
docs/api/src__apps__pages__20_Memos.py.md
docs/api/src__apps__pages__22_LLM_Scoreboard.py.md
docs/api/src__apps__pages__25_Recession.py.md
docs/api/src__apps__pages__27_Agents_Status.py.md
# ... (28 fichiers total)
```

**Raison**: Documenter Streamlit pages (legacy) n'a plus de sens

**Total**: 28 fichiers

---

### 2.2 API Docs Test Runners (13 fichiers)
```bash
docs/api/src__runners__test.py.md
docs/api/src__runners__test_app_integration.py.md
docs/api/src__runners__test_comprehensive.py.md
docs/api/src__runners__test_econ_llm_agent.py.md
docs/api/src__runners__test_fred_env.py.md
docs/api/src__runners__test_macro_fix.py.md
docs/api/src__runners__test_market_data.py.md
docs/api/src__runners__test_phase1_live.py.md
docs/api/src__runners__test_phase2_technical.py.md
# ... (13 fichiers total)
```

**Raison**: Test runners ne méritent pas API docs

**Total**: 13 fichiers

---

### 2.3 API Docs Stubs < 100 bytes (35 fichiers)
**Fichiers vides ou quasi-vides à régénérer**:
```bash
docs/api/src__apps__agent_app.py.md  # 15 bytes
docs/api/src__apps__pages__13_LLM_Models.py.md  # 19 bytes
docs/api/src__runners__test.py.md  # 97 bytes
# ... (35 fichiers total < 100 bytes)
```

**Raison**: Stubs sans contenu = pollution

**Total**: 35 fichiers

---

### 2.4 Docs UI Redondantes (3 fichiers)
**À fusionner dans `docs/architecture/ui-migration-guide.md`**:
```bash
docs/architecture/dash_migration.md
docs/architecture/dash_overview.md
docs/ui/ui_audit.md
```

**Total**: 3 fichiers (à fusionner, pas supprimer immédiatement)

---

### 2.5 Tests à Réorganiser (Déplacer, pas supprimer)
**Déplacer `tests/*.py` vers `tests/pages/`**:
```bash
tests/test_dashboard_page.py → tests/pages/
tests/test_signals_page.py → tests/pages/
tests/test_forecasts_page.py → tests/pages/
tests/test_deep_dive_page.py → tests/pages/
tests/test_backtests_page.py → tests/pages/
tests/test_evaluation_page.py → tests/pages/
tests/test_quality_page.py → tests/pages/
tests/test_agents_status_page.py → tests/pages/
tests/test_alerts_page.py → tests/pages/
tests/test_settings_page.py → tests/pages/
```

**Déplacer `tests/ui/test_routes.py` vers `tests/e2e/`**:
```bash
tests/ui/test_routes.py → tests/e2e/
```

**Déplacer `tests/tools/test_parquet_io.py` vers `tests/unit/`**:
```bash
tests/tools/test_parquet_io.py → tests/unit/
```

**Total**: 12 fichiers déplacés

---

## 🔴 PHASE 3: Long Terme (Q1 2026)

### 3.1 Streamlit Pages (28 fichiers)
**Suppression complète après deprecation**:
```bash
src/apps/pages/00_Home.py
src/apps/pages/1_Dashboard.py
src/apps/pages/2_News.py
src/apps/pages/3_Deep_Dive.py
src/apps/pages/4_Forecasts.py
src/apps/pages/5_Portfolio.py
src/apps/pages/6_Backtests.py
src/apps/pages/7_Reports.py
src/apps/pages/8_Evaluation.py
src/apps/pages/9_Screener.py
src/apps/pages/10_Advisors.py
src/apps/pages/11_Quality.py
src/apps/pages/12_Agents.py
src/apps/pages/13_LLM_Models.py
src/apps/pages/14_Regimes.py
src/apps/pages/15_Risk.py
src/apps/pages/16_Portfolio.py
src/apps/pages/17_Watchlist.py
src/apps/pages/18_Notes.py
src/apps/pages/19_Changes.py
src/apps/pages/20_Memos.py
src/apps/pages/21_Events.py
src/apps/pages/22_LLM_Scoreboard.py
src/apps/pages/23_Earnings.py
src/apps/pages/24_Settings.py
src/apps/pages/25_Recession.py
src/apps/pages/26_Observability.py
src/apps/pages/27_Agents_Status.py
src/apps/pages/__init__.py
```

**Total**: 28 fichiers, ~2,600 lignes

---

### 3.2 Streamlit Skeleton (17 fichiers)
```bash
src/apps/streamlit/__init__.py
src/apps/streamlit/layout.py
src/apps/streamlit/navigation.py
src/apps/streamlit/state.py
src/apps/streamlit/theme.py
# ... (17 fichiers total)
```

**Total**: 17 fichiers, ~400 lignes

---

### 3.3 Streamlit Support Apps (4 fichiers)
```bash
src/apps/agent_app.py
src/apps/forecast_app.py
src/apps/macro_sector_app.py
src/apps/stock_analysis_app.py
```

**Total**: 4 fichiers, ~500 lignes

---

### 3.4 Streamlit Main App (1 fichier, à remplacer par stub)
**Remplacer contenu de**:
```bash
src/apps/app.py
```

**Par stub**:
```python
"""
DEPRECATED: Streamlit UI removed in Q1 2026.
Please use Dash UI: http://localhost:8050
"""
import sys
print("❌ Streamlit UI has been removed.")
print("✅ Please use Dash UI: http://localhost:8050")
print("📖 Migration guide: docs/architecture/ui-migration-guide.md")
sys.exit(1)
```

**Total**: 1 fichier (830 lignes → 10 lignes)

---

## 📊 Récapitulatif par Phase

### Phase 1: Immédiat
| Catégorie | Fichiers | Taille | Action |
|-----------|----------|--------|--------|
| Old context | 1 | 522 KB | Supprimer |
| Artifacts phase1 | 71 | 884 KB | Supprimer |
| Tests redondants | 3 | ~150 lignes | Supprimer |
| Test runners | 11-13 | ~500 lignes | Archiver |
| Sprint reports | 6 | - | Déplacer |
| **TOTAL PHASE 1** | **92** | **~1.5 MB** | - |

---

### Phase 2: Court Terme
| Catégorie | Fichiers | Action |
|-----------|----------|--------|
| API docs Streamlit pages | 28 | Supprimer |
| API docs test runners | 13 | Supprimer |
| API docs stubs vides | 35 | Régénérer |
| Docs UI redondantes | 3 | Fusionner |
| Tests pages | 12 | Déplacer |
| **TOTAL PHASE 2** | **91** | - |

---

### Phase 3: Long Terme
| Catégorie | Fichiers | Lignes | Action |
|-----------|----------|--------|--------|
| Streamlit pages | 28 | ~2,600 | Supprimer |
| Streamlit skeleton | 17 | ~400 | Supprimer |
| Streamlit support apps | 4 | ~500 | Supprimer |
| Streamlit main app | 1 | 830 → 10 | Remplacer |
| **TOTAL PHASE 3** | **50** | **~3,500** | - |

---

## 🎯 TOTAL GÉNÉRAL

| Métrique | Quantité |
|----------|----------|
| **Fichiers à supprimer** | **183** |
| **Fichiers à déplacer** | **18** |
| **Fichiers à fusionner** | **3** |
| **Taille libérée** | **~3 MB** |
| **Lignes code supprimées** | **~4,150** |

---

## ✅ Commande Unique Phase 1 (Copier-Coller)

```bash
#!/bin/bash
# Cleanup Phase 1 - Exécution sécurisée

echo "🧹 Démarrage cleanup Phase 1..."

# Backup
git branch cleanup-backup-$(date +%Y%m%d)

# 1. Supprimer old context
if [ -f "docs/old-context/chat.md" ]; then
    rm -f docs/old-context/chat.md
    echo "✅ Old context supprimé"
fi

# 2. Supprimer artifacts phase1
if [ -d "artifacts_phase1" ]; then
    rm -rf artifacts_phase1/
    echo "✅ Artifacts phase1 supprimés"
fi

# 3. Supprimer tests redondants
rm -f tests/e2e/test_backtests_e2e.py
rm -f tests/e2e/test_evaluation_e2e.py
rm -f tests/test_pages.py
echo "✅ Tests redondants supprimés"

# 4. Archiver test runners
mkdir -p scripts/debug_archive
for file in src/runners/test*.py; do
    if [ -f "$file" ]; then
        mv "$file" scripts/debug_archive/
    fi
done
# Restaurer si utilisés en CI (décommenter si nécessaire):
# git checkout src/runners/sanity_runner.py
# git checkout src/runners/test_import_validation.py
echo "✅ Test runners archivés"

# 5. Réorganiser sprint reports
mkdir -p docs/sprints/archive
mv PROGRESS_SPRINT5.md docs/sprints/archive/ 2>/dev/null || true
mv SPRINT_SONNET_2_DELIVERY.md docs/sprints/archive/ 2>/dev/null || true
mv SPRINT_SONNET_2_REPORT.md docs/sprints/archive/ 2>/dev/null || true
mv MIGRATION_SPRINT11.md docs/sprints/archive/ 2>/dev/null || true
mv ARCHITECTURE_DELIVERY_SUMMARY.md docs/architecture/ 2>/dev/null || true
mv STREAMLIT.md docs/architecture/ 2>/dev/null || true
echo "✅ Sprint reports réorganisés"

# 6. Supprimer dossiers vides
rmdir docs/old-context 2>/dev/null || true

# Status
echo ""
echo "📊 Résumé cleanup:"
git status --short

echo ""
echo "✅ Cleanup Phase 1 terminé!"
echo "📝 Prochaine étape: git add -A && git commit -m 'chore(cleanup): phase 1'"
```

**Enregistrer comme**: `scripts/cleanup_phase1.sh`

**Exécuter**:
```bash
chmod +x scripts/cleanup_phase1.sh
./scripts/cleanup_phase1.sh
```

---

## 🔍 Vérification Post-Suppression

**Commandes de vérification**:
```bash
# 1. Vérifier fichiers supprimés
test ! -f docs/old-context/chat.md && echo "✅ Old context supprimé" || echo "❌ Échec"
test ! -d artifacts_phase1 && echo "✅ Artifacts supprimés" || echo "❌ Échec"
test ! -f tests/test_pages.py && echo "✅ Tests redondants supprimés" || echo "❌ Échec"

# 2. Vérifier déplacements
test -d docs/sprints/archive && echo "✅ Archive sprints créée" || echo "❌ Échec"
test -f docs/architecture/ARCHITECTURE_DELIVERY_SUMMARY.md && echo "✅ Docs déplacés" || echo "❌ Échec"

# 3. Tests passent toujours
pytest tests/ -q
echo "✅ Tests OK" || echo "❌ Tests échouent - vérifier"

# 4. Taille projet
du -sh . | awk '{print "Taille actuelle: "$1}'
```

---

## 📚 Références

- **Plan cleanup complet**: `docs/CLEANUP_PLAN.md`
- **Analyse détaillée**: `docs/CLEANUP_ANALYSIS_DETAILED.md`
- **Engineering rules**: `docs/dev/engineering_rules.md`

---

**Version**: 1.0
**Dernière mise à jour**: 2025-10-29
