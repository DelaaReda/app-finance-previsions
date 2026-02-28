# 🛠️ FRONTEND DATA DEBUGGING PROTOCOL

## 🎯 Objectif
Débloquer les pages UI bloquées par des données manquantes ou des chargements infinis en vérifiant les endpoints et en s'assurant qu'elles reçoivent des données réelles, pas des mocks.

## 📋 Checklist de Dépannage Frontend (à exécuter avant de déclarer une page "fonctionnelle")

### 1. Vérification Endpoint Directe
```bash
# Test les endpoints backend pour voir les données brutes
curl -sS http://localhost:8050/api/health | jq '{ok: .ok, status: .data?.status, updates: .data?.last_updates}'
curl -sS http://localhost:8050/api/forecasts | jq '{count: .data?.rows | length, first: .data?.rows[0]}'
curl -sS http://localhost:8050/api/news/feed | jq '{count: .data?.articles | length, first: .data?.articles[0]}'
curl -sS http://localhost:8050/api/macro/series | jq '{ok: .ok, has_data: (.data? | has("series"))}'
curl -sS http://localhost:8050/api/stocks/prices?ticker=SPY | jq '{ok: .ok, has_prices: (.data?.SPY?.prices | length > 0)}'
curl -sS http://localhost:8050/api/brief/daily | jq '{ok: .ok, has_summary: (.data?.summary != null)}'
curl -sS http://localhost:8050/api/backtests | jq '{ok: .ok, has_results: (.data?.results != null)}'
```

### 2. Vérification des Formats de Données
Pour chaque endpoint, assurez-vous que le format est correct:
- Structure `{ok: boolean, data: {...}}` obligatoire
- Collections (`articles`, `rows`, etc.) jamais `null`, toujours `[]` (même si vide)
- Données avec métadonnées de fraîcheur: `freshness`, `last_update`, `source`
- Aucun champ obligatoire manquant

### 3. Vérification Never-Empty
Tout accès aux données doit être "sure":
```ts
// ❌ MAUVAIS (cause des crashes)
const articles = data.articles.map(...) // Si data.articles est null → crash
const count = data.rows.length         // Si data.rows est null → crash

// ✅ BON (never-empty pattern)
import { ensureArray } from '@/lib/safe'  // ou '@/ui' si disponible

const articles = ensureArray(data?.articles || [])  // Retourne always []
const rows = ensureArray(data?.data?.rows || [])   // Protège les accès imbriqués

if (!rows.length) {
  return <EmptyState title="Aucune prévision disponible" hint="Le modèle calcule en arrière-plan..." />
}
```

### 4. Vérification des Routes API Coté Frontend
- S'assurer que le client API utilise le bon proxy: `VITE_API_BASE_URL=http://localhost:8050`
- Vérifier que les routes côté frontend correspondent aux endpoints backend
- Confirmer que le proxy Vite est correctement configuré pour rediriger `/api/*` vers le backend

### 5. Vérification des Hooks de Données
- Regarder les fichiers `src/hooks/use*.ts` pour voir comment les données sont récupérées
- Vérifier que les hooks gèrent correctement les états: loading, error, empty, success
- S'assurer que les helpers de sécurité sont utilisés (safe access)

## 🔧 Dépannage des Pages Bloquées

### Page Macro Bloquée (chargement infini)?
```bash
# Vérifier le format des données macro
curl -sS http://localhost:8050/api/macro/series?ids=CPIAUCSL | jq '.'

# Doit retourner une structure avec séries temporelles, pas une seule valeur
# Si le backend retourne un seul point au lieu d'une série historique → backend à corriger
```

### Page Stocks Bloquée (chargement infini)?
```bash
# Vérifier que l'endpoint renvoie des données de prix
curl -sS http://localhost:8050/api/stocks/prices?tickers=SPY | jq '{SPY_has_prices: .data?.SPY?.prices | length > 0}'

# Si "detail": "No price data" → ingestion de données côté backend à corriger
```

### Page Brief Bloquée (chargement infini)?
```bash
# Vérifier le format des données de brief
curl -sS http://localhost:8050/api/brief/daily | jq '.' 
curl -sS http://localhost:8050/api/brief/weekly | jq '.'

# Doit retourner des structures avec top_signaux, top_risks, etc.
```

## 🚨 Anti-Patterns Frontend à Réparer

1. **Accès direct à des propriétés potentiellement undefined**
   ```ts
   // ❌ Ne jamais faire
   data.items.map(...)  // Si data.items est undefined → error
   data.rows.length     // Si data.rows est undefined → error
   ```

2. **Réponses vides ou null dans les collections**
   ```ts
   // ❌ Ne jamais retourner
   { articles: null }   // Doit être { articles: [] }
   { rows: undefined }  // Doit être { rows: [] }
   ```

3. **Dates mal formatées**
   ```ts
   // ✅ Toujours gérer les deux formats: ISO string et Unix timestamp
   const formatDate = (date: string | number) => {
     if (typeof date === 'number') {
       return new Date(date * 1000).toISOString()  // Secondes → millisecondes
     }
     return new Date(date).toISOString()
   }
   ```

## 🧪 Tests Frontend à Exécuter

### 1. Tests Manuels
- Page chargée mais reste en "loading..." → problème d'endpoint ou format de données
- Page affiche "Cannot read property 'map' of undefined" → accès non sécurisé aux données
- Page vide sans message d'état → manque de gestion de l'état "empty"

### 2. Tests API via Frontend
```bash
# Simuler les appels que le frontend fait
curl -sS "http://localhost:5173/api/health" | jq '.'         # Si proxy fonctionne
curl -sS "http://localhost:5173/api/forecasts" | jq '.'      # Si proxy fonctionne
```

### 3. Vérification du Proxy Vite
```bash
# Vérifier la configuration dans vite.config.ts
# Doit rediriger /api/* vers http://localhost:8050
```

## 📦 Data Flow Vérification

### Backend → Frontend
1. Backend génère des données réelles dans `data/*.json` (ou parquet)
2. Endpoints API servent ces snapshots avec métadonnées
3. Frontend appelle les endpoints via proxy Vite
4. Hooks sécurisent les appels et protègent contre `undefined`
5. UI affiche les données ou un état vide propre

### Points de Contrôle
- [ ] Dossiers `data/` contiennent des fichiers avec des données réelles
- [ ] Endpoints `/api/*` retournent des réponses structurées avec `{ok, data}`
- [ ] Frontend reçoit bien les réponses via le proxy
- [ ] Hooks gèrent les erreurs et états vides correctement
- [ ] UI affiche des états propres sans crash

## 🧠 Résumé des Actions

**Avant de déclarer une page "fonctionnelle", chaque agent doit:**
1. Vérifier l'endpoint correspondant renvoie des données réelles (via curl)
2. S'assurer que les formats sont corrects et les données jamais nulles
3. Confirmer que les hooks de données gèrent les 4 états: loading, empty, error, success
4. Protéger tous les accès aux données avec les helpers never-empty
5. Tester la page dans des conditions réalistes (endpoint vide/erreur/mal formaté)

**Pour débloquer les pages bloquées actuellement:**
- Page News: [DONE] - Problème de parsing timestamp fixé
- Page Macro: [BLOQUÉE] - Backend renvoie snapshot au lieu de série temporelle
- Page Stocks: [BLOQUÉE] - Backend renvoie "No price data for screener" 
- Page Brief: [À VÉRIFIER] - Besoin de valider format de données
- Page Forecasts: [FONCTIONNELLE] - Données affichées correctement

**Prochaines étapes:**
1. Débloquer données backend pour Macro et Stocks
2. Mettre à jour les hooks avec formats corrects
3. Corriger les mappings de données dans les composants
4. Exécuter les tests de vérification pour chaque page