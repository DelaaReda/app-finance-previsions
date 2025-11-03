#!/bin/bash
# Script de nettoyage automatique pour prévenir la pollution du dossier racine

echo "🧹 Nettoyage automatique du dossier racine"
echo "==========================================="

# Compter les fichiers potentiellement indésirables
MD_FILES=$(find . -maxdepth 1 -name "*.md" -type f | wc -l)
PY_FILES=$(find . -maxdepth 1 -name "*.py" -type f | grep -v "test_" | wc -l)
TXT_FILES=$(find . -maxdepth 1 -name "*.txt" -type f | wc -l)

echo "📄 Fichiers Markdown dans racine: $MD_FILES"
echo "🐍 Fichiers Python dans racine: $PY_FILES" 
echo "📝 Fichiers texte dans racine: $TXT_FILES"

# Si des fichiers suspects sont trouvés, les déplacer
if [ $MD_FILES -gt 0 ] || [ $PY_FILES -gt 0 ] || [ $TXT_FILES -gt 0 ]; then
    echo "⚠️  Fichiers suspects détectés - déplacement en cours..."
    
    # Créer dossier de quarantaine s'il n'existe pas
    mkdir -p quarantine_$(date +%Y%m%d_%H%M%S)
    
    # Déplacer les fichiers suspects
    find . -maxdepth 1 -name "*.md" -type f -exec mv {} quarantine_$(date +%Y%m%d_%H%M%S)/_{}.bak \; 2>/dev/null || true
    find . -maxdepth 1 -name "*.py" -type f -not -name "test_*.py" -exec mv {} quarantine_$(date +%Y%m%d_%H%M%S)/_{}.bak \; 2>/dev/null || true
    find . -maxdepth 1 -name "*.txt" -type f -exec mv {} quarantine_$(date +%Y%m%d_%H%M%S)/_{}.bak \; 2>/dev/null || true
    
    echo "✅ Fichiers déplacés vers dossier de quarantaine"
else
    echo "✅ Aucun fichier suspect trouvé - dossier racine propre"
fi

echo "🎯 Nettoyage terminé"