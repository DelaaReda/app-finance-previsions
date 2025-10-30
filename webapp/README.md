# Copilote Financier - Interface React

Interface React moderne pour le copilote financier, implémentant la [VISION](../docs/VISION.md) du projet.

## 🚀 Démarrage rapide

```bash
# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
# → Ouvre http://localhost:5173

# Builder pour la production
npm run build

# Prévisualiser le build de production
npm run preview
```

## 📁 Structure du projet

```
src/
├── types/          # Types TypeScript (5 piliers)
├── services/       # Couche API vers backend Python
├── hooks/          # React Query hooks avec caching
├── components/     # Composants réutilisables
│   ├── layout/     # Header, Footer
│   ├── common/     # Card, LoadingSpinner, ErrorMessage
│   └── signals/    # TopSignals, TopRisks
├── pages/          # Pages principales (5 piliers)
│   ├── Dashboard.tsx
│   ├── Macro.tsx
│   ├── Stocks.tsx
│   ├── News.tsx
│   ├── Copilot.tsx
│   ├── MarketBrief.tsx
│   └── TickerSheet.tsx
├── api/            # Client API de base
└── app/            # Providers (React Query, etc.)
```

## 🎯 Pages implémentées

| Page | Route | Description | Pilier |
|------|-------|-------------|--------|
| Dashboard | `/` | Vue d'ensemble + Top 3 signaux/risques | - |
| Macro | `/macro` | FRED, VIX, GSCPI, GPR, inflation, emploi | 1 |
| Stocks | `/stocks` | Actions, indicateurs techniques, scoring | 2 |
| News | `/news` | Feed RSS avec scoring (freshness/source) | 3 |
| Copilot | `/copilot` | LLM Q&A avec RAG (≥5 ans contexte) | 4 |
| Brief | `/brief` | Daily/Weekly market briefs | - |
| Ticker | `/stocks/:ticker` | Fiche détaillée par ticker | 2 |

## 🔧 Configuration

### Proxy API

Le serveur Vite proxy automatiquement `/api/*` vers le backend Python:

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8050',
    changeOrigin: true,
  }
}
```

**Important**: Le backend Python doit tourner sur le port 8050.

### Variables d'environnement

Créer un fichier `.env.local` si nécessaire:

```env
VITE_API_URL=http://localhost:8050
```

## 📡 API Backend attendue

L'application attend les endpoints suivants du backend Python:

```
GET  /api/macro/dashboard
GET  /api/macro/series/:id
GET  /api/stocks/:ticker/analysis
GET  /api/news/feed
POST /api/copilot/query
GET  /api/copilot/rag/context
GET  /api/briefs/latest
```

Voir [REACT_MIGRATION.md](../docs/REACT_MIGRATION.md) pour la liste complète.

## 🎨 Conventions de code

### Types TypeScript
- Un fichier par pilier dans `src/types/`
- Export centralisé via `src/types/index.ts`
- Tous les types incluent traçabilité (sources + timestamps)

### Services
- Un service par pilier dans `src/services/`
- Utilise `apiGet` et `apiPost` de `src/api/client.ts`
- Gestion d'erreur centralisée

### Hooks
- React Query pour le caching
- Préfixe `use` obligatoire
- `staleTime` adapté au type de données:
  - Macro: 5-15 min
  - News: 2 min
  - Briefs: 15-30 min

### Composants
- PascalCase pour les noms
- Props typées avec TypeScript
- Inline styles pour l'instant (TODO: styled-components)

## 🧪 Tests

```bash
# Lancer les tests (TODO)
npm test

# Coverage (TODO)
npm run test:coverage
```

## 🐛 Debugging

### React Query Devtools
Active automatiquement en dev, accessible via le bouton flottant en bas à gauche.

### Problèmes courants

**Erreur 404 sur `/api/*`**
→ Le backend Python n'est pas lancé sur le port 8050

**Types TypeScript manquants**
→ Vérifier l'import depuis `@/types` (alias configuré dans tsconfig.json)

**React Query ne cache pas**
→ Vérifier la configuration `staleTime` dans les hooks

## 📚 Documentation

- **Vision du projet**: [../docs/VISION.md](../docs/VISION.md)
- **Architecture**: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Guide de migration**: [../docs/REACT_MIGRATION.md](../docs/REACT_MIGRATION.md)
- **Guide agent**: [../docs/AGENT_GUIDE.md](../docs/AGENT_GUIDE.md)

## 🚧 Prochaines étapes

### Priorité haute
- [ ] Implémenter les endpoints backend manquants
- [ ] Ajouter composants de graphiques (Recharts)
- [ ] Intégrer scoring composite 40/40/20
- [ ] Connecter RAG au Copilot

### Priorité moyenne
- [ ] Export briefs (HTML/PDF/MD)
- [ ] Système d'alertes temps réel
- [ ] Comparaisons sectorielles
- [ ] Tests unitaires + E2E

### Priorité basse
- [ ] Dark/Light mode toggle
- [ ] Responsive mobile
- [ ] Keyboard shortcuts
- [ ] Accessibilité ARIA

## 🤝 Contribution

Suivre les conventions dans [../docs/AGENT_GUIDE.md](../docs/AGENT_GUIDE.md).

## 📄 Licence

Voir [../LICENSE](../LICENSE)
