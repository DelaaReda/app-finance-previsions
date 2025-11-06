# 📊 DASHBOARD INTEGRATION PLAN - Tasks Division

This document outlines the tasks required to implement the new Dashboard with:
- Complete filters (Horizon, Universe, Themes)
- Macro sparklines (CPI & VIX AreaChart)
- Forecast cards (Top 5 + directional donut)
- News section
- Freshness system
- Never-empty protections

## FC-DASH-001 — Dashboard Component Implementation
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Implémenter le composant Dashboard.tsx avec Mantine + Tremor, filtres et layout.

**Fichiers**
* `frontend/webapp/src/pages/Dashboard.tsx`
* `frontend/webapp/src/ui/DashboardLayout.tsx`

**Étapes**
1. Créer la structure de base du Dashboard avec les filtres:
   - SegmentedControl pour Horizon (court/moyen/long)
   - MultiSelect pour Univers (tickers)
   - Input pour Thèmes (ex: growth, value, momentum)
2. Créer les sections de layout: Top Nav, Filters, Main Content Grid
3. Intégration des composants Card, BarList, Donut chart, AreaChart de Tremor
4. Connexion aux hooks de données

**DoD**
* Dashboard.tsx fonctionnel avec filtres interactifs
* Layout responsive avec Mantine Grid
* Tous les composants UI sont accessibles via `@/ui` ou Mantine/Tremor
* Aucun crash si données manquantes (never-empty patterns appliqués)

---

## FC-DASH-002 — Hooks Data & API Integration
**Status**: AVAILABLE to claim
**Owner**: Backend + Frontend teams

**But**: Créer les hooks React et les endpoints API pour alimenter le Dashboard.

**Fichiers**
* `frontend/webapp/src/hooks/useForecasts.ts`
* `frontend/webapp/src/hooks/useMacroSeries.ts`
* `frontend/webapp/src/hooks/useNews.ts`
* `backend/api/routes/forecasts.py`
* `backend/api/routes/macro.py`
* `backend/api/routes/news.py`

**Étapes**
1. **Frontend Hooks**:
   - Créer `useForecasts(options: { horizon, universe, themes })`
   - Créer `useMacroSeries(ids: string[])` pour CPI, VIX
   - Créer `useNews(options: { universe, limit })` avec sentiment si dispo
   - Utiliser `ensureArray`, `nn` pour never-empty

2. **API Endpoints**:
   - `/api/forecasts?horizon=short|medium|long&universe=SPY,QQQ&themes=growth,value,etc.`
   - `/api/macro/series?ids=CPIAUCSL,VIXCLS`
   - `/api/news?universe=SPY,QQQ&limit=6`

**DoD**
* Hooks utilisent les patterns never-empty (skeletons, fallbacks)
* Endpoints retournent structures conformes avec {ok, data} 
* Filtres du Dashboard propagent correctement aux appels API
* Aucun crash UI si hooks échouent

---

## FC-DASH-003 — Macro Sparklines (AreaChart Tremor)
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Implémenter les graphiques macro avec AreaChart Tremor et badges de fraîcheur.

**Fichiers**
* `frontend/webapp/src/components/charts/MacroAreaChart.tsx`
* `frontend/webapp/src/components/ui/FreshnessBadge.tsx`
* `frontend/webapp/src/pages/Dashboard.tsx`

**Étapes**
1. Créer composant `MacroAreaChart` avec Tremor AreaChart:
   - Supporte CPI, VIX, et autres séries macro
   - Responsive design
   - Tooltips et interactions
   - Gestion de loading/error/empty states

2. Intégrer FreshnessBadge pour chaque série:
   - Affiche dernière mise à jour
   - Couleur selon fraîcheur (green/fresh, yellow/stale, red/old)
   - Position dans le coin du chart

3. Connecter aux données réelles via useMacroSeries

**DoD**
* AreaCharts fonctionnels pour CPI et VIX (ou autres)
* Badges de fraîcheur visibles et correctement colorés
* Charts stylés avec Tremor + Mantine
* Aucun crash si données macro manquantes

---

## FC-DASH-004 — Forecast Cards (Top 5 + Directional Donut)
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Créer les cartes de prévisions avec BarList Tremor et donut directionnel.

**Fichiers**
* `frontend/webapp/src/components/forecasts/ForecastTop5.tsx`
* `frontend/webapp/src/components/forecasts/DirectionalDonut.tsx`
* `frontend/webapp/src/components/forecasts/ForecastCard.tsx`

**Étapes**
1. **Top 5 Prévisions**: 
   - BarList Tremor avec ticker, horizons, scores de prévision
   - Tri configurable (par confiance, retour attendu, etc.)
   - Couleurs selon direction (vert pour up, rouge pour down)

2. **Donut Directionnel**:
   - PieChart Tremor montrant répartition Up/Down/Flat
   - Calculé à partir des directions des prévisions
   - Légende claire avec pourcentages

3. **Carte de Prévision**:
   - Card Mantine avec ticker, horizon, direction, confidence
   - Couleur de bordure selon confiance
   - Niveau de détail configurable

4. Connecter aux données via useForecasts

**DoD**
* Top 5 affiché dans BarList responsive
* Donut directionnel montrant répartition Up/Down/Flat
* Cartes de prévision avec toutes les métadonnées
* Safe access pour éviter les crashes sur données incomplètes

---

## FC-DASH-005 — News Section & Sentiment Display
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Créer la section News avec affichage de sentiment et badges.

**Fichiers**
* `frontend/webapp/src/components/news/NewsSection.tsx`
* `frontend/webapp/src/components/news/NewsCard.tsx`
* `frontend/webapp/src/components/ui/NewsSentimentBadge.tsx`

**Étapes**
1. **News Section**:
   - Layout grid/list pour les articles
   - Affichage titre, résumé, source, date
   - Sentiment score si disponible (0-1, rouge/vert pour négatif/positif)
   - Filtrage par univers si disponible

2. **News Cards**:
   - Card Mantine avec données structurées
   - Badges pour tickers mentionnés
   - Indicateur de sentiment (couleur ou icône)
   - Lien cliquable vers article original

3. **Sentiment Badge**:
   - Badge coloré selon sentiment (rouge/négatif, vert/positif, gris/neutre)
   - Valeur numérique si disponible
   - Intégration dans la structure de NewsCard

4. Connecter aux données via useNews

**DoD**
* Section News affichant articles avec sentiments
* Badges de sentiment clairement visibles
* News Cards stylées avec Mantine
* Never-empty: affichage propre même si pas d'articles

---

## FC-DASH-006 — System Refresh & Freshness Management
**Status**: AVAILABLE to claim
**Owner**: Frontend team (coordination Backend si needed)

**But**: Implémenter les badges de fraîcheur centralisée et le bouton Refresh All.

**Fichiers**
* `frontend/webapp/src/contexts/RefreshContext.tsx`
* `frontend/webapp/src/components/system/FreshnessTracker.tsx`
* `frontend/webapp/src/components/system/RefreshAllButton.tsx`
* `frontend/webapp/src/pages/Dashboard.tsx`

**Étapes**
1. **Contexte Refresh**:
   - Créer RefreshContext avec état global pour timestamps de fraîcheur
   - Système de propagation des événements de refresh

2. **Tracked de Fraîcheur**:
   - Composant centralisé qui stocke les dernières dates de mise à jour
   - Synchronisé avec les réponses API (last_update, freshness fields)
   - Mise à jour des badges de fraîcheur en conséquence

3. **Bouton Refresh All**:
   - Déclenche le refresh de toutes les données simultanément
   - Indicateur de chargement global
   - Retour visuel sur l'état du refresh

4. Intégration avec tous les composants du Dashboard

**DoD**
* Badges de fraîcheur visibles sur toutes les sections
* Bouton Refresh All fonctionnel
* Contexte de refresh propagé correctement à tous les composants
* Système never-empty: fallback si refresh échoue

---

## Coordination required between:
- ALEX-API-ARCHITECT: Endpoints API pour les nouveaux filtres
- ALEX-FINANCE-ANALYST: Logique de tri des prévisions selon filtres
- MAXIMILIAN: Modèles ML pour les prédictions basées sur filtres
- ALEX-BACKEND: Pipeline d'ingestion pour données macro
- LENA: Integration des données dans le nouveau format