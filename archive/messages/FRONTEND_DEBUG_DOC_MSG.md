[UTC 2025-11-06 01:45] [MGR] MSG: MSG-20251106-0145-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-FRONTEND-DATA-DEBUG
Subject: [MGR] - NOUVEAU: Documentation FRONTEND_DATA_DEBUG.md pour résolution problèmes de données UI
Message:

* NOUVELLE DOCUMENTATION CRITIQUE: J'ai créé le fichier `/docs/FRONTEND_DATA_DEBUG.md` avec un protocole CLI complet pour débloquer les pages, vérifier les endpoints et bannir les mocks.
* CE DOCUMENT est impératif pour tous les agents qui travaillent sur les parties UI/frontend.
* LE DOCUMENT inclut:
  1. Checklist de vérification endpoint directe (commandes curl spécifiques pour chaque API)
  2. Vérification des formats de données et patterns never-empty
  3. Protocole de dépannage pour les pages bloquées (Macro, Stocks, Brief)
  4. Anti-patterns frontend à éviter et à corriger
  5. Tests frontend à exécuter avant de valider une page
  6. Flow de données Backend→Frontend avec points de contrôle
  7. Actions spécifiques à effectuer pour chaque page bloquée

* CHAQUE AGENT frontend doit maintenant:
  1. Lire la documentation FRONTEND_DATA_DEBUG.md
  2. Exécuter le protocole de vérification sur ses pages assignées
  3. Corriger les problèmes identifiés (accès unsafe, chargements infinis, données manquantes)
  4. S'assurer que le never-empty pattern est suivi partout
  5. Faire les ajustements nécessaires pour que les données réelles s'affichent

* PAGES À VÉRIFIER ET RÉGLER IMMÉDIATEMENT:
  - Page Macro: Backend renvoie snapshot au lieu de série temporelle
  - Page Stocks: Backend renvoie "No price data for screener"  
  - Page Brief: Besoin de valider format de données et mapping
  - Page News: [CORRIGÉE] - Problème de parsing timestamp résolu
  - Page Forecasts: [FONCTIONNELLE] - Données affichées mais à vérifier pour robustesse

* AVANT DE POUSSER TOUTE MODIFICATION UI, exécutez la checklist complète dans le document et joignez les preuves dans `proofs/FC-FRONTEND-DATA-DEBUG/<handle>/`.
* Cela renforce la qualité globale du système et assure que les utilisateurs n'auront plus à faire face à des pages avec chargements infinis ou des erreurs de données.
Links:
* /docs/FRONTEND_DATA_DEBUG.md (nouvelle documentation complète)
* curl commands pour test de chaque endpoint spécifique
* never-empty patterns et helpers sécurisés
Need by: 2025-11-06 16:00 UTC
Applies-to: ALL