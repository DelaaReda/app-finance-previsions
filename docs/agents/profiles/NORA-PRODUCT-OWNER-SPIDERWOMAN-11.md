# NORA-PRODUCT-OWNER-SPIDERWOMAN-11

- Rôle: Product Owner (background UI/UX Designer)
- Superhero: Spiderwoman
- Numéro: 11

## Mission Active
- Aligner l’UI sur une vision produit pro (MUI unifiée, états robustes, performance, accessibilité).
- Éliminer les incohérences de design system (MUI vs Mantine/Tremor), sécuriser les états (never-empty), et clarifier la navigation.

## Livrables créés dans ce sprint
- Backlog d’amélioration UI structuré: `docs/product/UI_IMPROVEMENT_BACKLOG.md`
- Plan d’amélioration du process équipe UI/Front: `docs/dev/UI_PROCESS_IMPROVEMENTS.md`

## État
- Fait
  - Audit UI complet (navigation, pages clés, helpers de sécurité, clients API).
  - Backlog priorisé avec DoD et preuves attendues.
- En cours
  - Cadrage de la standardisation MUI (remplacement Mantine/Tremor sur Dashboard, Macro, Stocks).
- Planifié
  - Unification des helpers de sécurité (`@/lib/safe` unique) et dépréciation de `@/utils/safeAccess`.
  - Normalisation des loaders (Skeleton), Empty States, Freshness badge sur toutes les vues.
  - Mise à jour des tests (Playwright) pour éviter ambiguïtés de sélecteurs.

## Critères de Qualité (DoD UI)
- Un seul design system (MUI) et un seul thème.
- Jamais de `.map`/`.length` sur valeurs non sûres (usage `safeArray`).
- Loading = Skeleton; Empty = EmptyState; Error = Alert; Freshness visible.
- Performances: temps d’affichage initial < 300ms, DataGrid paginé 25 par défaut.
- Accessibilité: focus visible, aria-labels sur composants interactifs, contrastes OK.

## Preuves exigées
- Captures Playwright (avant/après), logs réseau stables, sortie curl des endpoints.
- Lien vers commit et mini-demo (gif/video) si pertinent.

