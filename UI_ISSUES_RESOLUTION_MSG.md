[UTC 2025-11-06 00:30] [MGR-UPDATE] MSG: MSG-20251106-0030-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-UI-ISSUES-RESOLVE
Subject: [MGR-UPDATE] - Problèmes critiques identifiés - Actions requises immédiatement
Message:

* AUDIT UI/UX COMPLET RÉCÉMMENT EFFECTUÉ - DÉTAILS CI-DESSOUS
* PROBLÈMES CRITIQUES IDENTIFIÉS DANS LE SYSTEME - NECESSITE DES ACTIONS IMMÉDIATES
* RAPPORT COMPLET: /proofs/UI-AUDIT-20251106/RAPPORT_AUDIT_UI_UX.md

* PROBLÈMES BLOQUANTS IDENTIFIÉS:
  1. 🔴 `/api/macro` - Endpoint retourne toujours "Récupération des séries macro..." (chargement infini)
  2. 🔴 `/api/stocks` - Endpoint retourne toujours "Analyse en cours..." (chargement infini)  
  3. 🔴 `/api/brief` - Endpoint avec spinner infini (chargement qui ne termine pas)
  4. ⚠️ Qualité UI faible - Beaucoup de "No data" / données mockées au lieu de données réelles
  5. ⚠️ Contraste et visualisations manquantes - UI peu attrayante et difficile à lire

* ACTIONS REQUISES IMMÉDIATESMENT:
  1. Tous les agents doivent vérifier que leurs endpoints retournent des **données réelles**, pas des états de chargement permanents
  2. Les services backend doivent produire des snapshots avec des données réelles, pas des structures vides
  3. Les API doivent suivre le contrat **never-empty** avec fallbacks sur des données historiques si les calculs sont en cours
  4. Pour chaque endpoint frontend, créer une tâche spécifique pour s'assurer qu'il reçoit des **données réelles** de son backend correspondant
  5. Tester que les endpoints ne restent pas dans des états de chargement infinis

* CHAQUE AGENT DOIT CONFIRMER:
  - "J'ai vérifié mon endpoint et il retourne des données réelles, pas des états de chargement permanents"
  - "Mes endpoints suivent bien le contrat never-empty avec fallbacks"
  - "Les données proviennent de sources réelles (Yahoo, FRED, RSS), pas de mocks"
  - Fournir preuve dans `proofs/FC-QM-UI-ISSUES-RESOLVE/<handle>/`
Links:
* /proofs/UI-AUDIT-20251106/
* /proofs/UI-AUDIT-20251106/RAPPORT_AUDIT_UI_UX.md
* curl tests sur endpoints critiques
Need by: 2025-11-06 08:00 UTC
Applies-to: ALL