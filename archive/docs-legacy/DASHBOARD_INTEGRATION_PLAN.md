[UTC 2025-11-05 15:00] [MGR-UPDATE] MSG: MSG-20251105-1500-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-DASHBOARD-INTEGRATION
Subject: [MGR-UPDATE] - Nouvelle spécification Dashboard avec filtres complets + sparklines macro
Message:

* NOUVELLE SPÉCIFICATION PRÊTE À INTÉGRER: Dashboard complet avec filtres et visualisations macro
* L'architecture est prête avec Mantine + Tremor, incluant:
  1. Filtres complets (Horizon, Univers multi-tickers, Thèmes) qui propagent aux hooks
  2. Sparklines macro (CPI & VIX) en AreaChart Tremor avec badges de fraîcheur
  3. Cards "Prévisions – Top 5" (BarList) + donut directionnel (Up/Down/Flat)
  4. News propre avec sentiments/badges
  5. Système de fraîcheur centralisé + bouton "Refresh All"
  6. Protection never-empty (Skeletons, états vides, gestion d'erreurs)
* Je vais diviser cela en tâches spécifiques pour l'équipe avec instructions claires.
* Chaque agent devrait se coordonner pour implémenter cette spécification complète.
Links:
* Nouvelle tâche divisée dans TASKS_BOARD.md (sections FC-DASH-001 à FC-DASH-006)
* Copie du Dashboard.tsx dans /templates/dashboard/Dashboard.tsx
* docs/api_endpoints_required.md (nouveaux endpoints nécessaires)
Applies-to: ALL