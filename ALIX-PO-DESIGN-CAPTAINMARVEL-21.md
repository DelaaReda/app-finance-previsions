# ALIX-PO-DESIGN-CAPTAINMARVEL-21

## 🎯 Rôle & Focus
- Poste: Product Owner (background UI/UX designer)
- Missions immédiates: audit qualité UI, alignement contrat API ↔️ Front, montée en gamme de la démarche produit/design.
- Périmètre: Dashboard, Stocks, Macro, health widgets, design system Mantine/Tremor.

## ✅ Livré ce cycle
- Lecture expresse des règles projet (`AGENTS.md`, vision architecture, backlog produit) pour cadrer l’audit.
- Création backlog priorisé des chantiers UI critiques (ajoutés dans `TASKS_BOARD.md`).

## 🚧 En cours
- Audit complet des pages `/`, `/stocks`, `/macro`, `/news` pour cartographier gaps UX ↔️ vision (`data always available`, `never empty`).
- Diagnostic Design System: vérifier wrappers Mantine (`src/ui/index.tsx`) vs exigences accessibilité (forwardRef, aria-labels, modes).

## 📌 Prochaines étapes
1. Semaine 1
   - Obtenir validation dev leads sur tâches `FC-FE-API-CONTRACT-ALIGN` & `FC-FE-MANTINE-V7-HARDEN` (blocage console actuel).
   - Monter un mini spec « UI Health Contract » listant métriques & endpoints attendus pour Dashboard/HealthBar.
2. Semaine 2
   - Coordonner avec backend pour `FC-FE-STOCKS-LIVE-DATA` (contrat `/api/stocks/screener`).
   - Préparer maquette Figma (ou Markdown) pour états vides FR conformément à vision.

## 🤝 Besoins / Risques
- **Alignement API**: divergence `/api` vs `/` côté front bloque l’expérience; nécessite décision rapide.
- **Debt Mantine**: warnings actuels annoncent rupture future (v7); à traiter avant tout nouveau composant.
- **Données Stocks**: sans screener réel, la page ne respecte pas le principe « vraie data ». Priorité produit.

## 🧭 Indicateurs succès PO
- 0 warning console en navigation standard (objectif sous 48h).
- Pages critiques délivrent données réelles (Dashboard/Stocks/Macro/News) avec preuves screenshot + curl.
- Documentation front mise à jour pour éviter regressions (pattern PR template + proof checklist).
