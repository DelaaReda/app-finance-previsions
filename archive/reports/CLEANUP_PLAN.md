# 🧹 Plan de Nettoyage du Repository

**Date**: 2025-01-27  
**Agent**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77

## 📋 Fichiers à Nettoyer

### 1. Fichiers TEMP/URGENT/CRITICAL (à archiver)
- `TEMP_NEW_TASK.md`
- `TEMP_ADVANCED_INTEGRATION_PLAN.md`
- `TEMP_MESSAGE.md`
- `TEMP_VERIFICATION_MSG.md`
- `TEMP_UI_DIRECTIVE_MSG.md`
- `TEMP_JUDGE_MSG.md`
- `URGENT_COORDINATION_MSG.md`
- `URGENT_USER_ACTION_REQUIRED.md`
- `CRITICAL_ROUTING_ISSUE.md`
- `CRITICAL_REAL_DATA_TASKS.md`

### 2. Fichiers .bak/.backup (à supprimer - déjà dans archive)
- `AGENTS_MESSAGES.md.bak`
- `AGENTS_MESSAGES.md.backup`
- `TASKS_BOARD.md.bak`

### 3. Documentation legacy Dash/Streamlit (à archiver)
- `copilot-app/docs/architecture/dash_migration.md`
- `copilot-app/docs/architecture/dash_overview.md`
- `copilot-app/docs/architecture/vision.md` (contient références Dash/Streamlit)

### 4. Fichiers de logs/tests à la racine (à nettoyer)
- `api.log`
- `test_*.py` (à déplacer dans copilot-app/tests/)
- `test_*.sh` (à déplacer dans copilot-app/scripts/)

### 5. Fichiers de messages/rapports obsolètes (à archiver)
- `BACKEND_DATA_ISSUES_MSG.md`
- `BACKEND_DATA_TASKS_MSG.md`
- `EP_REAL_DATA_MSG.md`
- `FRONTEND_DEBUG_DOC_MSG.md`
- `COMPLETE_ALIGNMENT_MSG.md`
- `PROGRESS_RECOGNITION_MSG.md`
- `DELIVERY_VERIFICATION_REPORT.md`
- `CODACY_EXEC_REQUEST.md`
- `CODACY_INTEGRATION_MSG.md`
- `CODACY_TASKS_SECTION.md`
- `NEW_API_ENDPOINTS_TASKS.md`
- `NEW_ENDPOINTS_ANALYSIS.md`
- `NEW_FEATURE_SPEC.md`
- `NEW_TASKS.md`
- `ROUTING_FIX_TASK.md`
- `ROUTING_SUCCESS_UPDATE.md`
- `SAFE_HELPERS_FIX.md`
- `REAL_DATA_ISSUES_REPORT.md`
- `MICHEL_URGENT_DECISION.md`

### 6. Documentation UI obsolète (à archiver)
- `UI_FIXES_PAGE_VIDE.md`
- `UI_STABILIZATION_FIXES.md`
- `UI_ISSUES_RESOLUTION_MSG.md`
- `UI_QA_REQUEST.md`
- `UI_TESTING_PROCEDURE.md`
- `UI_AUDIT_IMPROVEMENTS_2025.md`
- `UI_AUDIT_PROFESSIONAL_2025.md`
- `VISUALIZATION_TEMPLATES_GUIDE.md`
- `MASTER_VISUALIZATION_TEMPLATES.md`
- `ULTRA_VISUALIZATION_TEMPLATES.md`
- `ADVANCED_VISUALIZATION_TEMPLATES.md`
- `INTEGRATION_VISUALIZATIONS_SUMMARY.md`
- `TEST_VISUAL_INSTRUCTIONS.md`

### 7. Fichiers de planification obsolète (à archiver)
- `DASHBOARD_TASKS_PLAN.md`
- `DASHBOARD_INTEGRATION_PLAN.md`
- `forecast_improvement_plan.md`

### 8. Fichiers agents (à organiser dans agents/)
- Tous les fichiers `*-*.md` (profils agents) → `agents/`

### 9. Fichiers de documentation copilot-app obsolète (à archiver)
- `copilot-app/CACHE_FIRST_IMPLEMENTATION.md`
- `copilot-app/CACHE_FIRST_SUMMARY.md`
- `copilot-app/AGENTS_CACHE_FIRST_GUIDE.md`
- `copilot-app/ARCHITECTURE_CACHE_FIRST.md`
- `copilot-app/SCREENSHOT_FIXES_SUMMARY.md`
- `copilot-app/UI_FIXES_SCREENSHOTS.md`
- `copilot-app/TIMEOUT_FIXES_AND_COPILOT_ACTIVATION.md`
- `copilot-app/LLM_JUDGE_PERFORMANCE_OPTIMIZATION.md`
- `copilot-app/UI_VERIFICATION_CHECKLIST.md`
- `copilot-app/UI_PERFORMANCE_OPTIMIZATION.md`
- `copilot-app/UI_DATA_DISPLAY_VALIDATION.md`
- `copilot-app/TEST_VALIDATION_REPORT.md`
- `copilot-app/DATA_VERIFICATION_REPORT.md`
- `copilot-app/INTEGRATION_FINAL_REPORT.md`
- `copilot-app/WIDGETS_INTEGRATION_COMPLETE.md`
- `copilot-app/PIPELINES_SUMMARY.md`
- `copilot-app/FRONTEND_HOOKS_CREATED.md`
- `copilot-app/PIPELINES_CREATED.md`
- `copilot-app/INVESTIGATION_PROCESS_APPLIED.md`
- `copilot-app/UI_DATA_FIX_PROGRESS.md`
- `copilot-app/INVESTIGATION_GUIDE.md`

## 📁 Structure cible

```
/mnt/utm/
├── archive/
│   ├── temp-urgent/          # Fichiers TEMP/URGENT/CRITICAL
│   ├── messages/              # Messages/rapports obsolètes
│   ├── docs-legacy/           # Documentation legacy Dash/Streamlit
│   ├── docs-ui-legacy/        # Documentation UI obsolète
│   └── copilot-app-legacy/    # Docs copilot-app obsolètes
├── agents/                    # Profils agents
├── copilot-app/               # Application principale
└── ...
```

