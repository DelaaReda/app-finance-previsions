#!/bin/bash
# Cleanup Phase 1 - App Finance Prévisions
# Date: 2025-10-29
# Objectif: Supprimer fichiers obsolètes, réorganiser docs

set -e  # Exit on error

echo "🧹 Démarrage cleanup Phase 1..."
echo ""

# Backup branch
BACKUP_BRANCH="cleanup-backup-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
echo "✅ Backup branch créé: $BACKUP_BRANCH"
echo ""

# 1. Supprimer old context (522 KB)
echo "📁 1/5: Suppression old context..."
if [ -f "docs/old-context/chat.md" ]; then
    rm -f docs/old-context/chat.md
    rmdir docs/old-context 2>/dev/null || true
    echo "   ✅ docs/old-context/chat.md supprimé (522 KB)"
else
    echo "   ⏭️  Fichier déjà supprimé"
fi
echo ""

# 2. Supprimer artifacts phase1 (884 KB)
echo "📁 2/5: Suppression artifacts phase1..."
if [ -d "artifacts_phase1" ]; then
    rm -rf artifacts_phase1/
    echo "   ✅ artifacts_phase1/ supprimé (71 fichiers, 884 KB)"
else
    echo "   ⏭️  Dossier déjà supprimé"
fi
echo ""

# 3. Supprimer tests redondants
echo "📁 3/5: Suppression tests redondants..."
DELETED_TESTS=0
for file in tests/e2e/test_backtests_e2e.py tests/e2e/test_evaluation_e2e.py tests/test_pages.py; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "   ✅ $file supprimé"
        ((DELETED_TESTS++))
    fi
done
if [ $DELETED_TESTS -eq 0 ]; then
    echo "   ⏭️  Tests déjà supprimés"
fi
echo ""

# 4. Archiver test runners obsolètes
echo "📁 4/5: Archivage test runners..."
mkdir -p scripts/debug_archive
MOVED_RUNNERS=0
for file in src/runners/test*.py; do
    if [ -f "$file" ]; then
        mv "$file" scripts/debug_archive/
        echo "   ✅ $(basename $file) → scripts/debug_archive/"
        ((MOVED_RUNNERS++))
    fi
done

# Restaurer sanity_runner et test_import_validation si utilisés en CI
if [ -f "scripts/debug_archive/sanity_runner.py" ]; then
    git checkout src/runners/sanity_runner.py 2>/dev/null || true
    echo "   ℹ️  sanity_runner.py restauré (utilisé en CI)"
fi
if [ -f "scripts/debug_archive/test_import_validation.py" ]; then
    git checkout src/runners/test_import_validation.py 2>/dev/null || true
    echo "   ℹ️  test_import_validation.py restauré (utilisé en CI)"
fi

if [ $MOVED_RUNNERS -eq 0 ]; then
    echo "   ⏭️  Runners déjà archivés"
fi
echo ""

# 5. Réorganiser sprint reports
echo "📁 5/5: Réorganisation sprint reports..."
mkdir -p docs/sprints/archive
mkdir -p docs/architecture

MOVED_DOCS=0
for file in PROGRESS_SPRINT5.md SPRINT_SONNET_2_DELIVERY.md SPRINT_SONNET_2_REPORT.md MIGRATION_SPRINT11.md; do
    if [ -f "$file" ]; then
        mv "$file" docs/sprints/archive/
        echo "   ✅ $file → docs/sprints/archive/"
        ((MOVED_DOCS++))
    fi
done

for file in ARCHITECTURE_DELIVERY_SUMMARY.md STREAMLIT.md; do
    if [ -f "$file" ]; then
        mv "$file" docs/architecture/
        echo "   ✅ $file → docs/architecture/"
        ((MOVED_DOCS++))
    fi
done

if [ $MOVED_DOCS -eq 0 ]; then
    echo "   ⏭️  Docs déjà réorganisés"
fi
echo ""

# Status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Résumé cleanup Phase 1:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
git status --short
echo ""

# Counts
DELETED_FILES=$(git status --short | grep -c "^ D" || echo "0")
MODIFIED_FILES=$(git status --short | grep -c "^ M" || echo "0")
UNTRACKED_DIRS=$(git status --short | grep -c "^??" || echo "0")

echo "📈 Statistiques:"
echo "   - Fichiers supprimés: $DELETED_FILES"
echo "   - Fichiers modifiés: $MODIFIED_FILES"
echo "   - Nouveaux dossiers: $UNTRACKED_DIRS"
echo ""

echo "✅ Cleanup Phase 1 terminé!"
echo ""
echo "📝 Prochaines étapes:"
echo "   1. Vérifier changements: git status"
echo "   2. Vérifier tests: make test"
echo "   3. Commit: git add -A && git commit -m 'chore(cleanup): phase 1 immediate cleanup'"
echo "   4. Push: git push origin main"
echo ""
echo "💡 En cas de problème, restaurer: git checkout $BACKUP_BRANCH"
