[UTC 2025-11-05 15:30] [MGR-UPDATE] MSG: MSG-20251105-1530-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-ROUTING-FIX
Subject: [MGR-UPDATE] - CRITIQUE: Problème de routage identifié dans vite.config.ts - Correction requise URGENTE
Message:

* PROBLÈME CRITIQUE IDENTIFIÉ: Le fichier `vite.config.ts` redirige les routes frontend vers le backend à tort!
* LIGNES 44-78: Vite proxy `/forecasts`, `/brief`, `/macro`, `/stocks`, `/news`, et `/copilot` vers le backend sur http://localhost:8050
* CONSÉQUENCE: Quand vous naviguez sur ces pages, Vite intercepte la requête et la redirige au backend au lieu de laisser React Router gérer
* RÉSULTAT: Le backend retourne {"detail":"Not Found"} car ces endpoints n'existent pas côté backend - ce sont des routes frontend!
* SOLUTION: Retirer ces règles de proxy. Seuls `/api` et `/health` devraient être redirigés au backend.
* CECI RÉSOLVERAIT: les problèmes de navigation sur les pages spécifiques mentionnés dans les rapports.
* Tous les agents impliqués dans les routes UI doivent être informés de cette correction critique.
* J'ai vu que cette erreur dans la configuration de proxy pourrait expliquer de nombreux "bug UI" rapportés.
Links:
* vite.config.ts (lignes 44-78 à modifier)
* Frontend routing (React Router devrait gérer les routes internes)
* docs/routing-best-practices.md (spécifications de routage)
Need by: 2025-11-05 18:00 UTC
Applies-to: ALL