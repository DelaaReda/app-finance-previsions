# 🛠️ FRONTEND DATA DEBUG PROTOCOL - Finance Copilot

## 🎯 But du document

Guide d'audit et de débogage des composants frontend pour s'assurer que:

* Les endpoints retournent **des données réelles** (jamais de mocks)
* Les pages ne crashent **jamais** (never-empty patterns)
* Les données sont **fraîches** et **cohérentes**
* L'UI affiche correctement les **états vides/sans données**

Ce protocole est à suivre **avant chaque push**.

---

## 🚨 Checklist : Page "casse" ou "loading infini"

Quand une page UI charge indéfiniment ou crash, suivre ce diagnostic :

### 1. Vérifier l'endpoint backend

```bash
# Exemple pour la page News
curl -sS http://localhost:8050/api/news/feed | jq .

# Exemple pour la page Forecasts  
curl -sS http://localhost:8050/api/forecasts | jq .

# Exemple pour la page Backtests
curl -sS http://localhost:8050/api/backtests | jq .

# Vérifier la forme
curl -sS http://localhost:8050/api/health | jq '{ok, data.status, data.last_updates}'
```

**Rechercher** :
* `{ok: true, data: {...}}` (bon format)
* `rows`, `articles`, `results`, `items` (collections pas `null`)
* `freshness`, `last_update`, `source` (méta-données)

### 2. Vérifier le proxy Vite

```bash
# Depuis frontend
curl -sS http://localhost:5173/api/health | jq .
curl -sS http://localhost:5173/api/forecasts | jq '.data.rows | length'

# Si ça échoue → problème de proxy dans vite.config.ts
```

### 3. Vérifier le hook React Query

```bash
# Dans la console dev, chercher les queries actives
console.log(queryClient.getQueryCache().findAll())
```

---

## 🔍 Débogage CLI : Procédure pas-à-pas

### Étape 1 : Vérifier l'état du backend

```bash
# 1. Health du backend
curl -sS :8050/api/health | jq '{ok, data.status, data.last_updates, data.data_paths}'

# 2. Chemins de données
ls -la copilot-app/data/  # Vérifier que les fichiers existent

# 3. Horodatage des snapshots
stat copilot-app/data/forecasts.json    # Date de dernière modification
stat copilot-app/data/news_feed.json    # Idem
stat copilot-app/data/brief_weekly.json # Idem
```

### Étape 2 : Tester les endpoints critiques

```bash
# Test des endpoints avec structure de réponse attendue
curl -sS :8050/api/forecasts | jq '{ok, data: {rows: .data.rows[:3], count: (.data.rows|length), freshness: .data.freshness, source: .data.source}}'
curl -sS :8050/api/news/feed | jq '{ok, data: {articles: .data.articles[:3], count: (.data.articles|length), freshness: .data.freshness}}'
curl -sS :8050/api/brief/daily | jq '{ok, data: {top_signals: (.data.top_signals|length), top_risks: (.data.top_risks|length)}}'
curl -sS :8050/api/macro/series | jq '{ok, data: {series: (.data.series|length)}}'
curl -sS :8050/api/backtests | jq '{ok, data: {results: (.data.results|length), overall_metrics: .data.overall_metrics}}'
```

### Étape 3 : Vérifier la fraîcheur des données

```bash
# Calculer la fraîcheur (en minutes depuis dernier update)
curl -sS :8050/api/health | jq -r '.data.last_updates.forecasts' | xargs -I {} date -d @{} +%s
# Comparer à date actuelle: date +%s
# Différence < 1440 minutes = fraîcheur quotidienne OK
```

### Étape 4 : Vérifier la structure des données

```bash
# S'assurer que les collections ne sont jamais `null`
curl -sS :8050/api/forecasts | jq '.data.rows | if type=="array" then "OK" else "ERROR: not array" end'
curl -sS :8050/api/news/feed | jq '.data.articles | if type=="array" then "OK" else "ERROR: not array" end'
curl -sS :8050/api/brief/daily | jq '.data.top_signals | if type=="array" then "OK" else "ERROR: not array" end'
```

---

## 🧪 Outils de vérification

### 1. Script de smoke test local

```bash
#!/bin/bash
# scripts/debug/check_front_data.sh

set -euo pipefail

echo "🔍 Vérification des endpoints backend..."
FAILURES=0

check_endpoint() {
  local ep=$1
  local jq_filter=$2
  local name=$3

  echo "→ $name ($ep)"
  if ! curl -sS :8050"$ep" | jq -e "$jq_filter" >/dev/null 2>&1; then
    echo "❌ $name: $(curl -sS :8050"$ep")"
    ((FAILURES++))
  else
    echo "✅ $name: OK"
  fi
}

check_endpoint "/api/health" ".ok" "Health status"
check_endpoint "/api/forecasts" ".data.rows" "Forecasts data" 
check_endpoint "/api/news/feed" ".data.articles" "News data"
check_endpoint "/api/brief/daily" ".data.top_signals" "Daily brief"
check_endpoint "/api/macro/series" ".data.series" "Macro series"
check_endpoint "/api/backtests" ".data.results" "Backtests results"

echo "🏁 $FAILURES échecs détectés"
exit $FAILURES
```

### 2. Vérification des contrats API

```bash
# Vérifier que les contrats sont respectés
curl -sS :8050/api/forecasts | jq '
  select(.ok == true) |
  select(.data != null) |
  select(.data.rows != null) |
  select((.data.rows | type) == "array") |
  "✅ Contrat forecasts respecté"
'

# Vérifier la présence des champs de fraîcheur
curl -sS :8050/api/forecasts | jq '
  select(.data.freshness != null) |
  select(.data.source != null) |
  "✅ Métadonnées présentes"
'
```

---

## 🚫 Anti-patterns (à bannir)

### 1. Données mockées

❌ **Jamais** dans une route:
```ts
// Mauvais
return { articles: [] }
// ou
return null
```

✅ **Toujours** format standard:
```ts
// Bon
return ok({ articles: [], freshness: "2025-11-04T10:00:00Z", source: ["fallback"] })
```

### 2. Accès non protégé

❌ **Jamais**:
```ts
// Mauvais
data.rows.map(...)  
// ou
articles.length
```

✅ **Toujours**:
```ts
// Bon
const rows = data?.rows ?? []
const articles = resp?.data?.articles ?? []
rows.map(...)
articles.length
```

### 3. Sans métadonnées

❌ **Jamais** endpoint sans:
```json
{
  "ok": true,
  "data": { ... },
  "freshness": "ISO-8601",
  "source": ["..."],
  "version": "..."
}
```

---

## 💡 Résolution des problèmes courants

### "Cannot read properties of undefined (reading 'map')"

1. Vérifier que l'endpoint renvoie `{ok, data:{rows: []}}` et pas juste `[...]`
2. Dans le hook, s'assurer que `data?.rows ?? []` est utilisé
3. Vérifier la structure `{ok: true, data: {...}}` côté backend

### "Page vide sans indication"

1. Vérifier que l'endpoint renvoie au moins `{ok: true, data: {rows: []}}`
2. S'assurer que le composant EmptyState est affiché si `rows.length === 0`
3. Vérifier que le badge de fraîcheur est visible

### "Données obsolètes"

1. Vérifier timestamp `freshness` dans la réponse
2. Comparer avec date actuelle
3. Si > 24h, relancer les jobs backend

---

## 🔁 Process de vérification avant push

1. **Backend UP**: `./finance-copilot.sh status`
2. **Endpoints OK**: `scripts/debug/check_front_data.sh`
3. **UI stable**: Ouvrir pages `/news`, `/forecasts`, `/brief`, `/backtests` → pas de crash
4. **Données réelles**: Vérifier que les endpoints renvoient des données, pas des mocks
5. **Fichiers lock supprimés**: `.locks/` vide ou à jour
6. **Commit clean**: Seulement les fichiers touchés, pas `git add -A`

---

## 📋 Audit rapide (3 min)

Exécuter dans un terminal:

```bash
# 1. Vérifier le backend
curl -s :8050/api/health | grep -i ok

# 2. Vérifier que les réponses ont le bon format
curl -s :8050/api/forecasts | jq '.ok and .data'

# 3. Vérifier que les collections existent
curl -s :8050/api/forecasts | jq '.data.rows | type == "array"'

# 4. Vérifier la fraîcheur
curl -s :8050/api/health | jq '.data.last_updates'

# 5. Lancer en local
npm run dev  # Front
./finance-copilot.sh start  # Full stack
```

---

## 🧠 Notes pour les agents

> Ce protocole est votre **ligne de vie** quand l'UI casse.
> Toujours commencer par les endpoints backend, pas le front.
> Zéro mock = zéro cache = zéro simulation dans les réponses.
> Never-empty = toujours une structure `{ok: true, data: {...}}` même si vide.

---

## 🧪 Exemples de commandes utiles

| Objectif | Commande |
|----------|----------|
| Test santé endpoint | `curl -s :8050/api/health \| jq '{ok, data.status}'` |
| Test réponses vides | `curl -s :8050/api/forecasts \| jq '.data.rows \| length'` |
| Test fraîcheur | `curl -s :8050/api/forecasts \| jq '.data.freshness'` |
| Test sources | `curl -s :8050/api/forecasts \| jq '.data.source'` |
| Test proxy | `curl -s :5173/api/health \| jq .` |
| Test structure | `curl -s :8050/api/forecasts \| jq '. \| has("ok") and has("data")'` |