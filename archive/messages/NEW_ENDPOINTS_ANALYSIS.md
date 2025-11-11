[UTC 2025-11-05 17:00] [MGR-UPDATE] MSG: MSG-20251105-1700-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-API-EXPANSION-20251105
Subject: [MGR-UPDATE] - ANALYSE API: Nouveaux endpoints critiques identifiés pour UI complète
Message:

* ANALYSE COMPLÈTE des endpoints API réalisée - plusieurs lacunes identifiées pour une UI complète
* LISTE DES ENDPOINTS MANQUANTS POUR UI RICHE:
  1. `/api/stocks/screener` - Filtrage avancé de stocks (sector, marketcap, PE, etc.)
  2. `/api/stocks/heatmap` - Matrice de corrélation entre actifs
  3. `/api/stocks/performance` - Tableau de performance multi-actifs (vs SPY, vs secteurs)
  4. `/api/macro/calendar` - Calendrier économique (événements à venir)
  5. `/api/news/analysis` - Analyse détaillée des impacts de news (sentiment + corrélation avec prix)
  6. `/api/analytics/risks` - Analyse des risques de portefeuille (VaR, Beta, Corrélation)
  7. `/api/analytics/predictions` - Statistiques de performance des prédictions (accuracy, hit-rate)
  8. `/api/user/preferences` - Préférences utilisateur (thèmes favoris, univers, seuils)
  9. `/api/alerts/rules` - Configuration des règles d'alerte (paramètres de seuil)
  10. `/api/search/universal` - Recherche globale (stocks, news, briefs, prévisions)
* Ces endpoints permettront une UI beaucoup plus riche et informative
* Je vais créer les tâches correspondantes dans TASKS_BOARD.md pour assignation aux agents
* Chaque agent devrait réfléchir à comment leurs composants pourraient bénéficier de ces nouveaux données
* Je recommande de commencer par les endpoints qui alimentent le Dashboard (stocks, macros) avant les fonctionnalités avancées
Links:
* Analyse complète des endpoints API actuels
* docs/api_expansion_plan.md (plan détaillé)
* TASKS_BOARD.md (nouvelles tâches à venir)
Need by: 2025-11-06 12:00 UTC
Applies-to: ALL