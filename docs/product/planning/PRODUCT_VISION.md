# PRODUCT VISION — Finance Copilot
_Document de référence pour tous les agents — mis à jour 2026-03-02 par admin-claude_
_Source: vision directe de venom (owner)_

---

## 🎯 Qui est l'utilisateur

**Profil:** Reda (venom) — professionnel non-expert en finance qui gère ses investissements personnels seul.

**Problème réel:** Ne pas avoir le temps de suivre les marchés, lire les news, analyser les secteurs chaque jour. Prendre des décisions d'investissement avec 3-10h de recherche actuellement.

**Cible initiale:** Usage 100% personnel. Pas de SaaS, pas d'utilisateurs externes pour l'instant.

---

## 💡 Proposition de valeur

> En 2-3 clics, économiser 3 à 10 heures de recherches quotidiennes pour rester à jour sur les marchés et prendre les bonnes décisions d'investissement assez tôt.

L'app remplace:
- Lire les news financières chaque matin
- Analyser manuellement les tendances de marché
- Chercher des avis sur or, argent, IA, Tesla, secteurs géopolitiques
- Décider quoi faire avec son portefeuille aujourd'hui

---

## 🏆 Fonctionnalités MVP (ordre de priorité)

### P0 — Vue Globale Marché (Dashboard principal)
- **Résumé du marché aujourd'hui** : tendances majeures, humeur générale (bullish/bearish/neutre)
- **Alertes importantes** : ce qui a changé depuis hier, ce qu'il ne faut pas rater
- **Indicateurs macro** : géopolitique, taux Fed, inflation, récession signal
- **Secteurs à surveiller** : IA, or, argent, énergie, tech, crypto — direction et momentum
- **Brief quotidien** : texte synthétique "Voilà ce qui compte aujourd'hui"

### P0 — Copilot Portfolio ("Que faire aujourd'hui ?")
- Input: décrire son portefeuille ou sélectionner ses actifs
- Output: recommandation concrète (hold/buy/sell/rééquilibrer) avec raisonnement
- Source: combine news récentes + signaux techniques + forecasts + macro
- Réponse en moins de 30 secondes

### P1 — Forecasts Multi-Assets
- **Actifs couverts:** SPY, QQQ, AAPL, NVDA, META, MSFT, TSLA, or (GLD), argent (SLV), BTC, énergie (XLE), IA sector
- **Horizons:** 1 jour, 1 semaine, 1 mois
- **Format:** direction (up/down/flat) + confiance % + pourquoi (3 bullets max)
- **Multi-IA Judge:** au moins 2 modèles analysent, 1 juge tranche → verdict final

### P1 — Deep Dive Asset Spécifique
- Chercher "or", "Tesla", "IA stocks" → analyse complète en 1 clic
- News récentes sur cet actif (fraîcheur < 10 min)
- Signaux techniques + macro contexte
- Question libre : "L'or va monter cette semaine ?" → analyse IA approfondie

### P2 — News Feed Intelligent
- Pas de liste de news brutes — résumés avec impact estimé sur le portefeuille
- Filtres: macro / secteur / actif spécifique
- Score d'importance (0-10) pour prioriser la lecture
- Sentiment (positif/négatif/neutre)

### P3 — Alertes & Surveillance
- Alertes sur seuils (ex: or > $2100 → notifier)
- Signaux géopolitiques (risque élevé détecté)
- Changements de régime (ex: Fed pivot probable)

---

## 🚫 Hors scope MVP (ne pas implémenter)

- Connexion à des comptes de courtage réels (Wealthsimple, etc.)
- Exécution d'ordres automatiques
- Partage social / collaboration
- Application mobile native
- Gestion de portefeuille complexe (optimisation Markowitz complète)
- Backtests sophistiqués (simple hit rate suffit pour MVP)
- Multi-utilisateurs / authentification

---

## ⚙️ Contraintes techniques

- **Coût runtime:** modèles gratuits ou très peu chers (g4f, groq, ollama, qwen)
- **Fraîcheur données:** gap de 10 minutes acceptable (pas de temps réel strict)
- **Performance UI:** réponse < 3 secondes pour le dashboard principal
- **Cache:** obligatoire sur tous les endpoints lourds
- **Infra:** VM Ubuntu UTM locale, pas de cloud coûteux

---

## 📊 Définition du succès MVP

L'app est MVP-complète quand venom peut:
1. Ouvrir le dashboard le matin → voir en 30 secondes si le marché est à risque ou opportunité
2. En 2 clics → savoir si son portefeuille actuel est OK pour aujourd'hui
3. Chercher "or" → avoir une analyse + forecast en moins de 15 secondes
4. Poser une question → réponse avec raisonnement en moins de 30 secondes

---

## 🗺️ Roadmap Batches (plan de livraison agents)

### ✅ BATCH-01 — Contrats API (DONE)
Stabilisation des 5 endpoints MVP: health, stocks, news, forecasts, copilot/ask

### ✅ BATCH-02 — Multi-ticker + news (DONE)
Extension endpoints multi-ticker, filtres news, contract robustesse

### 🔄 BATCH-03 — Frontend Live + Qualité Données (EN COURS)
- frontend_engineer: connecter apiConnector.js à tous les widgets
- backend_engineer: corriger confidence forecasts, stocks change=0
- data_analyst: activer backtests, corriger pipeline données

### 📋 BATCH-04 — Dashboard Vision (À FAIRE)
- Brief quotidien fonctionnel (texte synthèse marché du jour)
- Secteurs vue globale avec direction et momentum réels
- Signaux macro (Fed, inflation, géopolitique)
- KPIs dashboard connectés aux vraies données

### 📋 BATCH-05 — Copilot "Que faire aujourd'hui ?" (À FAIRE)
- Endpoint copilot/ask amélioré avec contexte marché injecté automatiquement
- UI copilot: input portefeuille → output recommandation structurée
- Réponse < 30 secondes avec sources citées

### 📋 BATCH-06 — Forecasts Multi-Assets + Judge (À FAIRE)
- Coverage: or, argent, Tesla, secteur IA, énergie, crypto
- Multi-modèle: au moins 2 fournisseurs LLM analysent
- Judge IA: arbitre et donne verdict final avec confiance
- Horizons: 1d, 1w, 1m

### 📋 BATCH-07 — Deep Dive + News Intelligence (À FAIRE)
- Recherche par actif: analyse complète en 1 clic
- News résumées avec score d'impact (pas brutes)
- Question libre → analyse approfondie avec données fraîches

### 📋 BATCH-08 — Decision UX 2-3 clics + Flux portefeuille (À FAIRE)
- Parcours principal simplifié: dashboard → recommandation en 2-3 clics max
- Contrat décision unifié API→UI (verdict, confidence, why, risk)
- Validation UX nominal + dégradé (desktop/mobile)

### 📋 BATCH-09 — Alertes & Surveillance orientées décision (À FAIRE)
- Alertes seuils actifs + signaux macro priorisés
- Déduplication et hiérarchisation des alertes in-app
- SLA opérationnel sur latence d’alerte et faux positifs

### 📋 BATCH-10 — Cost/Runtime Governance + Release Gate MVP (À FAIRE)
- Gouvernance coût runtime (cache/fallback/quotas/timeouts)
- Gate release MVP complet (preuves API/UI/clickpath/robustesse)
- Décision GO/NO-GO avec plan de rollback explicite

### 📋 BATCH-11 — Data Ingestion Core + Freshness SLO (À FAIRE)
- Stabiliser ingestion multi-sources (prix, news, macro) avec fallback explicite
- Endpoint `ingestion/health` + observabilité des erreurs par source
- Garantir fraîcheur mesurée (SLO) et propagation jusqu'à l'UI

### 📋 BATCH-12 — Portfolio State + Risk Profile Core (À FAIRE)
- Persistance portefeuille/watchlist/profil de risque (local-first)
- Copilot branché sur portefeuille sauvegardé (sans resaisie)
- Flux UI d'édition robuste avec récupération en mode dégradé

### 📋 BATCH-13 — Decision Journal + Outcome Feedback Loop (À FAIRE)
- Journaliser chaque recommandation (contexte, verdict, confidence, horizon)
- Évaluer outcomes (hit rate, calibration) en 1d/1w/1m
- Exposer revue hebdo des décisions pour améliorer le backlog produit

### 📋 BATCH-14 — Finalisation Core v2: Robustness Drills + GO/NO-GO (À FAIRE)
- Drills de robustesse (provider down, stale data, timeout, restart)
- Validation parcours complet nominal + dégradé
- Gate final de production avec verdict GO/NO-GO et plan J+7

### 📋 BATCH-15 — Strategy Playbooks Engine (À FAIRE)
- Playbooks de décision par régime de marché et profil de risque
- Copilot piloté par stratégie explicite (pas seulement signal brut)
- Avertissement explicite en cas de conflit stratégie/signal

### 📋 BATCH-16 — Scenario and Stress Testing Lite (À FAIRE)
- Moteur what-if sur chocs macro et actifs
- Estimation impact portefeuille + action recommandée
- Vue UI simple pour comparer 5+ scénarios standards

### 📋 BATCH-17 — Regime Detection + Allocation Drift Alerts (À FAIRE)
- Détection changement de régime (risk-on, risk-off, transition)
- Alertes de dérive allocation vs posture cible
- Matrice posture recommandée par régime

### 📋 BATCH-18 — Event Driven Copilot (À FAIRE)
- Calendrier macro + earnings intégré dans le raisonnement
- Timeline événements à fort impact sur 24-48h
- Copilot sensible au timing (proximité événementielle)

### 📋 BATCH-19 — Explainability Graph + Source Traceability (À FAIRE)
- Graphe d'explication: sources, poids, fraîcheur, contribution
- Traçabilité claire de chaque recommandation
- Indicateurs qualité source visibles en UI

### 📋 BATCH-20 — Personal Policy Guardrails (À FAIRE)
- Garde-fous utilisateur: max risque, exclusions, limites position
- Blocage ou downgrade des recommandations hors politique
- Workflow override explicite et auditable

### 📋 BATCH-21 — Paper Trading Simulator + Execution Journal (À FAIRE)
- Simulation exécution (paper trading) depuis recommandations
- Journal exécution et qualité de fill (slippage/fees)
- Boucle apprentissage recommandation -> exécution -> outcome

### 📋 BATCH-22 — Rebalancing Optimizer Lite (À FAIRE)
- Optimiseur de rééquilibrage simple sous contraintes
- Proposition en 1 écran: turnover, delta risque, respect politique
- Maintien portefeuille rapide en quelques minutes

### 📋 BATCH-23 — Tax, Fees, and Slippage Awareness (À FAIRE)
- Estimation coûts/frictions par décision
- Affichage impact brut vs net
- Alertes quand l'edge net devient trop faible

### 📋 BATCH-24 — Alerting Intelligence V2 (À FAIRE)
- File d'alertes priorisée avec déduplication
- Contrôle fatigue (snooze/ack) et urgences top queue
- Meilleur signal, moins de bruit

### 📋 BATCH-25 — Autonomous Morning Brief Pipeline (À FAIRE)
- Génération automatique du brief matinal
- Section top 3 actions + risques clés
- Fallback dégradé explicite en cas d'échec

### 📋 BATCH-26 — Weekly Investment Committee Mode (À FAIRE)
- Pack hebdo: ce qui a changé, ce qui a marché, next actions
- Mode UI type comité d'investissement personnel
- Discipline hebdo avec suivi des carry-over actions

### 📋 BATCH-27 — Reliability SRE Pack + Chaos Drills (À FAIRE)
- Dashboard SLO (uptime, latence, queue health)
- Drills chaos: provider out, lock contention, restart failure
- Corrections de résilience avant automatisation plus large

### 📋 BATCH-28 — MVP v3 Release Gate + Adoption Analytics (À FAIRE)
- Gate final consolidé GO/NO-GO avec preuves complètes
- Métriques adoption et utilité quotidienne réelle
- Validation E2E nominal + dégradé avant exploitation continue

### 📋 BATCH-29 — Probabilistic Forecast Calibration Lab (À FAIRE)
- Calibration probabiliste des scores de confiance par horizon
- Diagnostics (Brier-like, reliability curves) visibles et versionnés
- Gate de qualité forecast avant extension fonctionnelle

### 📋 BATCH-30 — Multi-Horizon Forecast Decomposition (À FAIRE)
- Décomposer les drivers de prévision en 1d/1w/1m
- Expliquer divergences court/moyen terme
- Cartes UI de décomposition pour lecture rapide

### 📋 BATCH-31 — Cross-Asset Correlation Regime Map (À FAIRE)
- Carte corrélations multi-actifs + détection shifts de régime
- Contexte corrélation injecté dans briefs et analyses
- Vue heatmap orientée recherche

### 📋 BATCH-32 — Forecast Ensemble Governance (À FAIRE)
- Pondération dynamique multi-provider selon fiabilité récente
- Fallback dégradé contrôlé sans rupture de contrat
- Gouvernance explicite de drift d'ensemble

### 📋 BATCH-33 — Macro Narrative-to-Signal Parser (À FAIRE)
- Transformer narratifs macro en facteurs structurés
- Taxonomie facteur standardisée et auditable
- Facteurs injectés dans analyses/prévisions

### 📋 BATCH-34 — Alternative Data Sentiment Fusion (À FAIRE)
- Fusion sentiment/data alternatives avec pondération qualité
- Contribution sentiment visible dans la prévision
- Contrôle du bruit via weighting par source

### 📋 BATCH-35 — Forecast Drift Sentinel + Auto-Recalibration (À FAIRE)
- Détection drift des signaux et distributions de prévision
- Recalibration automatique avec audit trail et rollback
- Alerting drift opérationnel

### 📋 BATCH-36 — Uncertainty Visualization UX (À FAIRE)
- Bandes d'incertitude (p10/p50/p90) en UI
- Langage anti-surconfiance dans les insights
- Vérification couverture réelle vs intervalles prévus

### 📋 BATCH-37 — Hypothesis Workbench (À FAIRE)
- Atelier de recherche: hypothèse -> analyse -> prévision
- Historique hypothèses et résultats
- Workflow structuré pour analyse itérative

### 📋 BATCH-38 — Walk-Forward Forecast Scoreboard (À FAIRE)
- Scoreboard continu de performance prévisionnelle
- Qualité par actif et horizon dans le temps
- Alertes explicites quand la barre de qualité chute

### 📋 BATCH-39 — Forecast Data Quality SLA + Provenance (À FAIRE)
- Provenance complète de chaque payload de prévision
- SLA qualité/fraîcheur monitorés en continu
- Intégrité provenance validée par QA

### 📋 BATCH-40 — Predictive Research Hub Finalization Gate (À FAIRE)
- Gate final centré analyse/prévision (pas exécution trading)
- Validation E2E question -> forecast -> evidence
- Rapport tendance qualité forecast non-régressive

### 📋 BATCH-41 — Free Global Signal Mesh (À FAIRE)
- Catalogue et ingestion de sources gratuites multi-couches
- Contrats unifiés source/provenance/fraîcheur
- Gate conformité licences et coût runtime

### 📋 BATCH-42 — Geopolitical Risk Graph + Conflict Escalation (À FAIRE)
- Graphe risques géopolitiques et escalade par région
- Contribution géopolitique explicite dans les prévisions
- Carte monde/continent/secteur orientée impact

### 📋 BATCH-43 — Law and Policy Change Impact Engine (À FAIRE)
- Détection changements de lois/régulations (sources publiques)
- Propagation impact juridique vers secteurs/entreprises
- Timeline des dates d'effet et risque associé

### 📋 BATCH-44 — Insider Behavior Intelligence Layer (À FAIRE)
- Signaux comportement insiders depuis sources publiques
- Contribution insider transparente et non déterministe
- Panel company-level avec caveats explicites

### 📋 BATCH-45 — Supply Chain + Commodity Shock Propagation (À FAIRE)
- Modèle de propagation choc matière/logistique
- Chaîne d'impact monde -> secteur -> entreprise
- Hypothèses versionnées avec bornes d'incertitude

### 📋 BATCH-46 — Country/Continent/World Macro Regime Forecasts (À FAIRE)
- Prévisions hiérarchiques par pays, continent, monde
- Contrôles de cohérence inter-niveaux
- Dashboard drilldown multi-échelles

### 📋 BATCH-47 — Sector-to-Company Impact Transmission (À FAIRE)
- Transmission signaux secteur vers entreprise
- Décomposition direct/indirect des impacts
- Dégradation confiance si transmission incertaine

### 📋 BATCH-48 — Event Impact Horizon Matrix (À FAIRE)
- Matrice événement -> impact 1d/1w/1m
- Explication des divergences par horizon
- Lecture rapide en UI forecast lab

### 📋 BATCH-49 — Multi-Layer Forecast Fusion + Attribution (À FAIRE)
- Fusion des couches: géopolitique, lois, insiders, macro, secteur, entreprise
- Attribution par couche stable et explicable
- Vue top contributeurs positifs/négatifs

### 📋 BATCH-50 — Global Forecast Board Final Gate (Free Data) (À FAIRE)
- Gate final global multi-couches avec preuves E2E
- Confirmation usage de données gratuites en nominal
- Rapport de qualité par couche et horizon

## 🎯 Positionnement produit (clarification)
- Le produit est **forecast-first et analysis-first**.
- Il sert à **analyser, anticiper et prioriser l'information**, pas à exécuter des ordres.
- Les sorties doivent privilégier probabilités, incertitude, scénarios et facteurs explicatifs.
- Les pipelines doivent privilégier des **sources gratuites/publiques** avec traçabilité, qualité et conformité licence.

---

## 📌 Règles pour les agents

1. **Toujours relire ce fichier avant de planifier** — c'est la source de vérité
2. **Priorité P0 avant P1 avant P2** — ne pas sauter des étapes
3. **Chaque batch = une valeur démontrable** — pas de batch purement technique sans bénéfice visible
4. **Preuve obligatoire** — chaque livraison doit avoir une commande curl ou screenshot UI
5. **Coût runtime** — éviter d'appeler des LLMs coûteux en boucle, utiliser le cache
6. **2-3 clics max** — si une feature nécessite plus de 3 clics, simplifier l'UX
7. **Batches indépendants** — pas de dépendances bloquantes entre batches; dispatch parallèle autorisé avec garde-fous QA
