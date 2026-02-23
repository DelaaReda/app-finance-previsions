#!/bin/bash

# Script de validation du fichier marker
RUN_ID="20251212-001810"
MARKER_PATH="/Users/venom/Documents/analyse-financiere/copilot-app/backend/.qwen_runs/${RUN_ID}/marker.txt"

echo "Vérification du fichier marker pour run_id: ${RUN_ID}"

if [ -f "$MARKER_PATH" ]; then
    echo "✓ Le fichier marker existe: $MARKER_PATH"
    
    # Vérifier qu'il contient le bon run_id
    if grep -q "run_id=${RUN_ID}" "$MARKER_PATH"; then
        echo "✓ Le fichier marker contient le bon run_id"
    else
        echo "✗ Le fichier marker ne contient pas le bon run_id"
        exit 1
    fi
    
    # Vérifier qu'il contient created_at
    if grep -q "created_at=" "$MARKER_PATH"; then
        echo "✓ Le fichier marker contient created_at"
    else
        echo "✗ Le fichier marker ne contient pas created_at"
        exit 1
    fi
    
    echo "✓ Toutes les validations ont réussi"
    exit 0
else
    echo "✗ Le fichier marker n'existe pas: $MARKER_PATH"
    exit 1
fi