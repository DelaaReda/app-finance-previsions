# ADRIEN-PO-UX-BLACKPANTHER-17 — Product Owner (UI/UX)

## Rôle & Vision
- Rôle: Product Owner avec background UI/UX Designer
- Objectif: UI toujours stable, rapide, lisible; données réelles partout; zéro écran vide; navigation fluide, états explicites (freshness, source, erreurs contrôlées)

## Livraisons (cette session)
- Hotfix Brief (daily): corrigé import cassé (`from storage import load_json` → `from storage.io import load_json`).
- News feed: filtre tickers robuste + fallback never-empty quand aucun match; évite pages vides sous filtre.
- LLM Judge: endpoint réparé (fallback sur `forecasts.json` + import `json` manquant) → retourne des lignes réelles même sans stack modèles.
- Exécution Playwright (sans mocks): lancé et artefacts produits (screenshots/vidéos) pour audit UI.

Preuves:
- Endpoints:
  - `curl http://localhost:8050/api/brief/daily` → ok avec données (plus d’erreur import).
  - `curl -X POST /api/llm/judge/run {tickers:"AAPL,MSFT,SPY"}` → `count>0` avec rows filtrées.
  - `curl /api/news/feed?tickers=SPY,QQQ&limit=20` → `count=20` (fallback contrôlé).
- UI tests: artefacts Playwright dans `copilot-app/frontend/webapp/test-results/` (screenshots + vidéos).

## Constats UI (alignés VISION)
- News: l’application d’un filtre tickers aboutit souvent à 0 (données sources peu étiquetées). Solution: fallback + messaging clair.
- LLM Judge: avant, page vide/erreurs; maintenant interface stable + exécution renvoyant des lignes.
- Brief: snapshot daily/weekly doit toujours charger (cache-first). Import cassé résolu.
- Tests: beaucoup de tests échouent (sélecteurs fragiles/attentes trop strictes); nécessite stabilisation test-side et UI-side (guards visibles, ids de test, loaders cohérents).

## Backlog PO → Dev (priorité)
1) UI Never-Empty Guards (toutes pages)
   - Ajouter `EmptyState` standardisé + bandeau source/freshness sur chaque vue.
   - Exposer `data.generated_at`, `data.freshness`, `data.source` systématiquement.
2) News UX
   - Filtre tickers: si 0 match → afficher message “Aucun match, derniers articles affichés (fallback)” + badge.
   - Introduire chips de filtres actives + bouton “Réinitialiser”.
3) Judge UX
   - Conserver derniers paramètres (localStorage) et afficher `rows` + résumé (min_conf, max_er) avec badges.
   - Bouton “Télécharger JSON” des résultats.
4) Dashboard Cohérence
   - Tous les widgets: états de chargement unifiés; `aria-label`/`data-testid` stables.
   - Harmoniser les couleurs (Mantine theme), typographies et espacements.
5) Playwright Stabilisation (no mocks)
   - Ajouter `data-testid` pour éléments clés; synchronisations sur API (`page.waitForResponse(/\/api\//)`).
   - Captures par page (success + failure) dans `proofs/ui/`.
6) API Contracts
   - Normaliser `ok,data,error` et enveloppes; clamp `limit<=200` côté client.
   - Ajouter `note` quand fallback appliqué (News, Judge, Brief).

## Workflow équipe — améliorations
- Gate “never-empty”: PR refusée si une page peut rendre “vide” sans message.
- Seed de données: job doc “comment régénérer forecasts/news/local” avant tests.
- Playwright: réutiliser le serveur existant (ok) + scénario “sanity minimal” obligatoire.
- Convention `data-testid`: checklist par page (navigation, titre, tableau, state empty, state error).

## En cours
- Revue des tests Playwright échoués et proposition de `data-testid` par page.

## À venir
- UI status panel global (en-tête): santé backend, freshness global, horodatage last refresh.

