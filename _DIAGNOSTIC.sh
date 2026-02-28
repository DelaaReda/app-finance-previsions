#!/bin/bash
echo "=== DIAGNOSTIC SYSTÈME COMPLET ==="
echo ""
echo "1️⃣ État Planner (pas de boucle infinie?)"
ps aux | grep -i "planner\|cron" | grep -v grep | head -5

echo ""
echo "2️⃣ URLs documentées - Vérifier que le frontend a les bons endpoints"
grep -r "apiConnector\|API_BASE\|fetch.*api" apps/web/src 2>/dev/null | head -10

echo ""
echo "3️⃣ Vérifier que les forecasts existent et sont utilisés"
ls -lh apps/api/src/domains/forecasts/

echo ""
echo "4️⃣ Tâches BATCH-03 - Voir l'état réel vs ce qui est documenté"
grep -r "BATCH-03\|frontend_engineer\|backend_engineer\|data_analyst" memory/agents/ 2>/dev/null | head -10

echo ""
echo "5️⃣ État des sessions tmux (combien actives?)"
tmux list-sessions 2>/dev/null || echo "SSH needed"

echo ""
echo "6️⃣ Logs backend récents"
tail -20 logs-codex-runs/*/executor-monitoring.log 2>/dev/null | head -30

