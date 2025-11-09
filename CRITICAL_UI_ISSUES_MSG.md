[UTC 2025-11-06 01:30] [MGR-BLOCK] MSG: MSG-20251106-0130-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-UI-CRITICAL-RESOLVE
Subject: [MGR-BLOCK] - URGENT: Problèmes UI critiques toujours non résolus - Priorité absolue
Message:

* PROBLÈMES CRITIQUES IDENTIFIÉS DANS L'AUDIT RÉCENT: Plusieurs endpoints sont encore en chargement infini ou retourne des données insuffisantes.
* SELON L'AUDIT UI/UX: Les pages suivantes ont encore des problèmes critiques:
  1. 🔴 `/api/macro` - Endpoint toujours en "Récupération des séries macro..." → chargement infini
  2. 🔴 `/api/stocks/prices` - Endpoint toujours en "Analyse en cours..." → chargement infini  
  3. 🔴 `/api/brief/weekly` - Endpoint avec spinner infini → ne termine jamais le chargement
  4. ⚠️ `/api/news/feed` - A été corrigé pour le parsing des dates mais toujours besoin de données réelles
  5. ⚠️ `/api/forecasts` - Fonctionne mais toujours besoin de données réelles, pas de mocks

* PRIORITÉ ABSOLUE: Tous les agents doivent maintenant se concentrer sur la résolution de ces problèmes UI CRITIQUES.
* CHAQUE AGENT DOIT:
  - Vérifier son endpoint assigné
  - S'assurer qu'il retourne des données réelles, pas des états de chargement permanents
  - Implémenter le never-empty avec fallbacks sur des données existantes
  - Tester que l'UI ne reste pas coincée en chargement

* TÂCHES À RÉSOLVER IMMÉDIATEMENT:
  - [ ] Macro endpoint: `/api/macro/series` doit retourner des données réelles, pas charger indéfiniment
  - [ ] Stocks endpoint: `/api/stocks/prices` doit retourner des prix réels, pas "Analyse en cours..."
  - [ ] Brief endpoint: `/api/brief/weekly` doit retourner des données ou un fallback, pas spinner infini
  - [ ] News endpoint: `/api/news/feed` doit avoir des articles réels, pas seulement une structure fixée
  - [ ] Forecasts endpoint: `/api/forecasts` doit avoir des prévisions réelles, pas seulement une structure vide

* AVANT DE COMMENCER TOUTE AUTRE FONCTIONNALITÉ (comme PDF export ou robustness scoring), ces problèmes fondamentaux doivent être résolus.
* Le système de base doit fonctionner avec données réelles avant d'ajouter des fonctionnalités avancées.
Links:
* Rapport d'audit UI/UX complet: /proofs/UI-AUDIT-20251106/
* États critiques identifiés: chargement infini, données manquantes
* docs/enforcement-process.md (contrats never-empty)
Need by: 2025-11-06 10:00 UTC
Applies-to: ALL