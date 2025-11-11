[UTC 2025-11-05 16:00] [MGR-UPDATE] MSG: MSG-20251105-1600-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-SAFTY-HELPER
Subject: [MGR-UPDATE] - FIX CRITIQUE: Safe access helpers ajoutés pour éviter les crashes UI
Message:

* FIX CRITIQUE APPLIQUÉ: Problème `ensureArray is not defined` résolu pour éviter les crashes UI.
* J'ai créé les helpers de sécurité d'accès dans `frontend/webapp/src/lib/safe.ts`:
  - `ensureArray`: convertit toute valeur en tableau (ou tableau vide) pour éviter `.map` sur `undefined`
  - `nn`: valeur ou fallback pour éviter `null/undefined` access
  - `hasItems`, `safeLength`, `safeMap`, `safeGet`: helpers pour accès sécurisé
* J'ai mis à jour `frontend/webapp/src/ui/index.tsx` pour exporter ces helpers via `@/ui`
* Les agents peuvent maintenant importer ces helpers avec `import { ensureArray, nn } from '@/ui'`
* Cela permet de suivre les patterns never-empty et d'éviter les crashes comme: "Cannot read property 'map' of undefined"
* Tous les composants devraient utiliser ces helpers pour protéger contre les données vides.
* Cela résout le crash dans ForecastCardsWidget qui a déclenché ce travail de qualité.
Links:
* frontend/webapp/src/lib/safe.ts (helpers de sécurité implémentés)
* frontend/webapp/src/ui/index.tsx (exports mis à jour pour facile accès)
* docs/never-empty-patterns.md (guidelines de sécurité UI)
Need by: 2025-11-05 18:00 UTC
Applies-to: ALL