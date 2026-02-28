# PRODUCT VISION — Finance Copilot
_Document de référence pour tous les agents — mis à jour 2026-02-28 par admin-claude_
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

---

## 📌 Règles pour les agents

1. **Toujours relire ce fichier avant de planifier** — c'est la source de vérité
2. **Priorité P0 avant P1 avant P2** — ne pas sauter des étapes
3. **Chaque batch = une valeur démontrable** — pas de batch purement technique sans bénéfice visible
4. **Preuve obligatoire** — chaque livraison doit avoir une commande curl ou screenshot UI
5. **Coût runtime** — éviter d'appeler des LLMs coûteux en boucle, utiliser le cache
6. **2-3 clics max** — si une feature nécessite plus de 3 clics, simplifier l'UX

