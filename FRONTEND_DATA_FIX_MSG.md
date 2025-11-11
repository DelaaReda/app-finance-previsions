[UTC 2025-11-06 02:15] [MGR-UPDATE] MSG: MSG-20251106-0215-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-FRONTEND-DATA-FIX
Subject: [MGR-UPDATE] - URGENT: Documentation FRONTEND_DATA_DEBUG.md créée - Résolvez les problèmes de data dans UI immédiatement
Message:

* URGENT POUR TOUTES LES ÉQUIPES FRONTEND: J'ai créé la documentation complète `/docs/FRONTEND_DATA_DEBUG.md` avec protocole CLI détaillé pour résoudre les problèmes de données dans l'UI.
* CETTE DOCUMENTATION est essentielle pour débloquer les pages bloquées par des données manquantes ou des chargements infinis.
* LA DOCUMENTATION inclut:
  1. Commandes spécifiques pour tester chaque endpoint backend directement
  2. Vérifications de format de données et patterns never-empty à appliquer
  3. Procédures de dépannage pour les pages spécifiques (Macro, Stocks, Brief, News)
  4. Anti-patterns frontend à éviter et à corriger immédiatement
  5. Tests frontend à exécuter avant de valider une page comme fonctionnelle
  6. Flow de données Backend→Frontend avec points de contrôle

* CHAQUE AGENT FRONTEND doit maintenant:
  1. Lire immédiatement la documentation `/docs/FRONTEND_DATA_DEBUG.md`
  2. Exécuter le protocole de vérification sur les pages assignées
  3. Corriger les problèmes identifiés (accès unsafe, chargements infinis, données manquantes)
  4. S'assurer que les patterns never-empty sont suivis partout
  5. Fournir preuve dans `proofs/FC-QM-FRONTEND-DATA-FIX/<handle>/` avec captures et tests

* PAGES CRITIQUES À DÉBLOQUER IMMÉDIATEMENT:
  - Page Macro: Backend renvoie snapshot au lieu de série temporelle → bloquée avec chargement infini
  - Page Stocks: Backend renvoie "No price data" → bloquée avec chargement infini  
  - Page Brief: Besoin de valider format de données et mapping frontend
  - Page News: Problème de parsing timestamp à finaliser
  - Pages Forecasts: Fonctionnelles mais à vérifier pour robustesse

* AVANT DE POUSSER TOUTE MODIFICATION SUR UNE PAGE UI, exécutez la checklist complète dans le document et joignez les preuves dans `proofs/FC-QM-FRONTEND-DATA-FIX/<handle>/`.
* Cela garantira que les utilisateurs n'auront plus à faire face à des pages avec chargements infinis ou des erreurs de données.
* TOUTES LES PAGES doivent maintenant respecter le contrat never-empty: structure valide même si pas de données (pas de crash, pas de chargement infini).
Links:
* /docs/FRONTEND_DATA_DEBUG.md (nouvelle documentation complète à suivre)
* curl commands pour test de chaque endpoint spécifique
* never-empty patterns et helpers sécurisés à utiliser partout
* backend endpoints à vérifier: /api/forecasts, /api/macro/series, /api/stocks/prices, /api/news/feed, /api/brief/daily
Need by: 2025-11-06 18:00 UTC
Applies-to: ALL-FRONTEND-AGENTS