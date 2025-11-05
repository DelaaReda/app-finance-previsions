# TÂCHES STABILISATION UI + THÈME MUI - AGENTS

**Créé par** : CLAUDE-STABILITY-ARCHITECT-IRONMAN-42
**Date** : 2025-11-05
**Priorité** : 🔴 CRITIQUE
**Pour** : Agents Qwen (instructions détaillées pas-à-pas)

---

## 🎯 OBJECTIF GLOBAL

Stabiliser toutes les pages UI existantes et finaliser la migration vers Material-UI (MUI) pour :
- ✅ **Zéro crash** : Éliminer tous les crashs `.map()` / `.length` sur `undefined`
- ✅ **UI cohérente** : Thème MUI uniforme sur toutes les pages
- ✅ **Never-empty pattern** : États loading/error/empty clairs partout
- ✅ **UX professionnelle** : Composants MUI modernes et accessibles

**Points disponibles** : 600+ pts

---

## ⚠️ RÈGLES CRITIQUES (À LIRE AVANT DE COMMENCER)

### 1. TOUJOURS utiliser `safeArray()` avant `.map()`

❌ **MAUVAIS** (cause des crashs) :
```tsx
{data.items.map(item => ...)}  // CRASH si data.items est undefined!
```

✅ **BON** :
```tsx
import { safeArray } from '@/lib/safe';
{safeArray(data?.items).map(item => ...)}
```

### 2. TOUJOURS gérer 3 états : loading, error, empty

✅ **STRUCTURE OBLIGATOIRE** :
```tsx
if (isLoading) return <Skeleton variant="rounded" height={200} />;
if (error) return <Alert severity="error">Message d'erreur</Alert>;
if (!hasItems(data)) return <EmptyState title="Aucune donnée" />;

// Puis render normal
```

### 3. TOUJOURS donner un `id` stable aux rows DataGrid

❌ **MAUVAIS** :
```tsx
<DataGrid rows={items} ... />  // items sans id → crash
```

✅ **BON** :
```tsx
const rows = safeArray(items).map((item, i) => ({
  id: item.id ?? `fallback-${i}`,
  ...item
}));
<DataGrid rows={rows} ... />
```

### 4. JAMAIS modifier les endpoints backend dans ces tâches

- ⚠️ Ces tâches sont **FRONTEND SEULEMENT**
- ✅ Utiliser les endpoints existants tels quels
- ✅ Adapter le frontend pour tolérer différents formats de réponse

---

## 📦 PRÉREQUIS (À FAIRE UNE SEULE FOIS)

**Qui** : Premier agent qui commence une tâche UI
**Durée** : 10 min
**Points** : +20 pts

### Étape 1 : Installer dépendances MUI

```bash
cd copilot-app/frontend/webapp
pnpm add @mui/material @emotion/react @emotion/styled @mui/icons-material @fontsource/roboto @mui/x-data-grid
```

### Étape 2 : Créer fichiers helpers

**Fichier 1** : `src/lib/safe.ts`
```typescript
// Helper functions to prevent crashes
export function safeArray<T>(v: T[] | null | undefined): T[] {
  return Array.isArray(v) ? v : [];
}

export function hasItems<T>(v: T[] | null | undefined): boolean {
  return Array.isArray(v) && v.length > 0;
}

export function safeString(v: any): string {
  return v != null ? String(v) : '';
}

export function safeNumber(v: any, fallback: number = 0): number {
  const n = Number(v);
  return isNaN(n) ? fallback : n;
}
```

**Fichier 2** : `src/components/EmptyState.tsx`
```tsx
import { Box, Typography } from '@mui/material';
import InboxIcon from '@mui/icons-material/Inbox';

interface Props {
  title: string;
  hint?: string;
}

export default function EmptyState({ title, hint }: Props) {
  return (
    <Box sx={{ textAlign: 'center', py: 6 }}>
      <InboxIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
      <Typography variant="h6" color="text.secondary">{title}</Typography>
      {hint && <Typography variant="body2" color="text.disabled">{hint}</Typography>}
    </Box>
  );
}
```

**Fichier 3** : `src/components/FreshnessBadge.tsx`
```tsx
import { Chip } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

interface Props {
  stale?: boolean;
  lastUpdate?: string;
}

export default function FreshnessBadge({ stale, lastUpdate }: Props) {
  if (stale) {
    return (
      <Chip
        icon={<AccessTimeIcon />}
        label="Données anciennes"
        size="small"
        color="warning"
        variant="outlined"
      />
    );
  }

  return (
    <Chip
      icon={<CheckCircleIcon />}
      label="À jour"
      size="small"
      color="success"
      variant="outlined"
    />
  );
}
```

**Critères de validation** :
- [ ] `pnpm add` a réussi sans erreur
- [ ] Les 3 fichiers créés compilent sans erreur
- [ ] `pnpm dev` démarre sans erreur

---

## 🔥 TÂCHE 1 : FC-UI-NEWS-001 - Stabiliser page News (+80 pts)

**Priorité** : 🔴 CRITIQUE (crash actuel)
**Durée** : 1h
**Agent recommandé** : Tout agent disponible
**Dépendances** : PRÉREQUIS

### Problème actuel

Error dans logs : `Cannot read properties of undefined (reading 'length')` sur News.tsx ligne XX.

### Solution à implémenter

**Fichier** : `copilot-app/frontend/webapp/src/pages/News.tsx`

**IMPORTANT** :
1. ⚠️ NE PAS modifier les imports existants de votre code
2. ✅ AJOUTER les imports MUI nécessaires
3. ✅ REMPLACER le JSX de render par la version ci-dessous

```tsx
// AJOUTEZ ces imports EN HAUT du fichier
import { useQuery } from '@tanstack/react-query';
import {
  Alert, List, ListItem, ListItemText, Chip, Stack,
  Skeleton, Link, Typography, Box, Card, CardContent
} from '@mui/material';
import NewspaperIcon from '@mui/icons-material/Newspaper';
import EmptyState from '@/components/EmptyState';
import FreshnessBadge from '@/components/FreshnessBadge';
import { safeArray, hasItems } from '@/lib/safe';

// DANS votre composant News, REMPLACEZ le return par :
export default function News() {
  // Gardez votre useQuery existant, exemple :
  const { data, isLoading, error } = useQuery({
    queryKey: ['news', 'feed'],
    queryFn: async () => {
      const res = await fetch('/api/news/feed');
      return res.json();
    },
  });

  // ÉTATS : loading, error, empty - TOUJOURS dans cet ordre
  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="text" width={200} height={40} />
        <Skeleton variant="rounded" height={220} sx={{ mt: 2 }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Impossible de charger les actualités. Veuillez réessayer plus tard.
        </Alert>
      </Box>
    );
  }

  // EXTRAIRE les articles de manière TOLÉRANTE (ne crash jamais)
  // Essaie plusieurs chemins possibles dans la réponse
  const articles = safeArray(
    data?.data?.articles ??
    data?.articles ??
    data?.items
  );

  const stale = !!(data?.stale ?? data?.data?.stale);

  // Si aucun article, afficher EmptyState
  if (!hasItems(articles)) {
    return (
      <Box sx={{ p: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
          <NewspaperIcon color="primary" />
          <Typography variant="h5">Actualités Financières</Typography>
        </Stack>
        <EmptyState
          title="Aucun article disponible"
          hint="Ajustez les filtres ou revenez plus tard."
        />
      </Box>
    );
  }

  // RENDER normal avec données
  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <NewspaperIcon color="primary" />
        <Typography variant="h5">Actualités Financières</Typography>
        <FreshnessBadge stale={stale} lastUpdate={data?.last_update} />
      </Stack>

      <Card>
        <List>
          {articles.map((article, index) => {
            // ID stable pour chaque article
            const articleId = article.id ?? article.url ?? `article-${index}`;

            return (
              <ListItem
                key={articleId}
                divider={index < articles.length - 1}
                alignItems="flex-start"
                secondaryAction={
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {safeArray(article.tickers).slice(0, 3).map(ticker => (
                      <Chip key={ticker} size="small" label={ticker} />
                    ))}
                  </Stack>
                }
              >
                <ListItemText
                  primary={
                    article.url ? (
                      <Link href={article.url} target="_blank" rel="noreferrer">
                        {article.title || 'Sans titre'}
                      </Link>
                    ) : (
                      <Typography>{article.title || 'Sans titre'}</Typography>
                    )
                  }
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="text.primary">
                        {article.source || 'Source inconnue'}
                      </Typography>
                      {' · '}
                      {article.published_at || article.date || '—'}
                    </>
                  }
                />
              </ListItem>
            );
          })}
        </List>
      </Card>

      {articles.length > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          {articles.length} article{articles.length > 1 ? 's' : ''} affiché{articles.length > 1 ? 's' : ''}
        </Typography>
      )}
    </Box>
  );
}
```

### Checklist de validation

- [ ] Page charge sans crash (vérifier console)
- [ ] Skeleton s'affiche pendant loading
- [ ] Alert s'affiche en cas d'erreur (tester en coupant le backend)
- [ ] EmptyState s'affiche si `articles = []`
- [ ] Liste s'affiche correctement avec données réelles
- [ ] Tickers affichés en Chips
- [ ] Aucune erreur dans la console browser
- [ ] Badge "À jour" / "Données anciennes" s'affiche

### Preuve requise

Screenshot de :
1. Page en loading (skeleton)
2. Page avec données (liste articles)
3. Console sans erreur

---

## 🔥 TÂCHE 2 : FC-UI-FORECASTS-002 - Stabiliser page Forecasts (+100 pts)

**Priorité** : 🔴 CRITIQUE
**Durée** : 1h30
**Agent recommandé** : Tout agent disponible
**Dépendances** : PRÉREQUIS

### Solution à implémenter

**Fichier** : `copilot-app/frontend/webapp/src/pages/Forecasts.tsx`

```tsx
// IMPORTS
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Alert, Typography, Skeleton, Box, Stack, Card
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import FreshnessBadge from '@/components/FreshnessBadge';
import EmptyState from '@/components/EmptyState';
import { safeArray, hasItems } from '@/lib/safe';

export default function Forecasts() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['forecasts'],
    queryFn: async () => {
      const res = await fetch('/api/forecasts');
      return res.json();
    },
  });

  // TOUJOURS dans cet ordre : loading → error → empty → normal
  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="text" width={250} height={40} />
        <Skeleton variant="rounded" height={400} sx={{ mt: 2 }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Impossible de charger les prévisions. Vérifiez que le backend est démarré.
        </Alert>
      </Box>
    );
  }

  const stale = !!(data?.stale ?? data?.data?.stale);

  // Extraction TOLÉRANTE des données
  const rawItems = safeArray(
    data?.data?.items ??
    data?.items ??
    data?.data?.forecasts ??
    data?.forecasts ??
    data?.rows
  );

  // CRITIQUE : Ajouter un ID stable à chaque row pour DataGrid
  const rows = rawItems.map((item, index) => ({
    id: item.id ?? item.symbol ?? `forecast-${index}`,
    ...item,
  }));

  if (!hasItems(rows)) {
    return (
      <Box sx={{ p: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
          <TrendingUpIcon color="primary" />
          <Typography variant="h5">Prévisions</Typography>
        </Stack>
        <EmptyState
          title="Aucune prévision disponible"
          hint="Les prévisions sont générées quotidiennement à 4h AM."
        />
      </Box>
    );
  }

  // Définir les colonnes du DataGrid
  const columns = useMemo<GridColDef[]>(() => [
    { field: 'symbol', headerName: 'Symbole', width: 120 },
    { field: 'type', headerName: 'Type', width: 110 },
    { field: 'horizon', headerName: 'Horizon', width: 110 },
    { field: 'direction', headerName: 'Direction', width: 110 },
    {
      field: 'score',
      headerName: 'Score',
      width: 100,
      type: 'number',
      valueFormatter: (params) => {
        const val = params.value;
        return val != null ? Number(val).toFixed(2) : '—';
      },
    },
    {
      field: 'confidence',
      headerName: 'Confiance',
      width: 110,
      type: 'number',
      valueFormatter: (params) => {
        const val = params.value;
        return val != null ? `${(Number(val) * 100).toFixed(1)}%` : '—';
      },
    },
    {
      field: 'expected_return',
      headerName: 'Rendement',
      width: 110,
      type: 'number',
      valueFormatter: (params) => {
        const val = params.value;
        return val != null ? `${(Number(val) * 100).toFixed(2)}%` : '—';
      },
    },
  ], []);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <TrendingUpIcon color="primary" />
        <Typography variant="h5">Prévisions</Typography>
        <FreshnessBadge stale={stale} lastUpdate={data?.last_update} />
      </Stack>

      <Card>
        <DataGrid
          rows={rows}
          columns={columns}
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          autoHeight
          disableRowSelectionOnClick
          sx={{
            border: 0,
            '& .MuiDataGrid-cell:focus': {
              outline: 'none',
            },
          }}
        />
      </Card>

      <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
        {rows.length} prévision{rows.length > 1 ? 's' : ''} disponible{rows.length > 1 ? 's' : ''}
      </Typography>
    </Box>
  );
}
```

### Checklist de validation

- [ ] Page charge sans crash
- [ ] DataGrid s'affiche avec données
- [ ] Pagination fonctionne
- [ ] Tri par colonne fonctionne
- [ ] Aucune erreur "id" dans console
- [ ] EmptyState si aucune donnée
- [ ] Badge freshness s'affiche

### Preuve requise

Screenshot de DataGrid avec données + console sans erreur

---

## 🔥 TÂCHE 3 : FC-UI-DASHBOARD-003 - Stabiliser Dashboard (+90 pts)

**Priorité** : 🟡 ÉLEVÉE
**Durée** : 1h30
**Dépendances** : PRÉREQUIS

### Solution

**Fichier** : `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`

```tsx
import { useQuery } from '@tanstack/react-query';
import {
  Alert, Grid, Card, CardContent, Typography, Skeleton, Stack, Box
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningIcon from '@mui/icons-material/Warning';
import FreshnessBadge from '@/components/FreshnessBadge';
import EmptyState from '@/components/EmptyState';
import { safeArray, hasItems, safeString } from '@/lib/safe';

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const res = await fetch('/api/dashboard');
      return res.json();
    },
  });

  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="text" width={200} height={40} sx={{ mb: 2 }} />
        <Grid container spacing={2}>
          {[1, 2, 3, 4].map(i => (
            <Grid key={i} item xs={12} sm={6} md={3}>
              <Skeleton variant="rounded" height={120} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Erreur de chargement du dashboard</Alert>
      </Box>
    );
  }

  const stale = !!(data?.stale ?? data?.data?.stale);

  // Extraction TOLÉRANTE
  const kpis = safeArray(data?.data?.kpis ?? data?.kpis);
  const topSignals = safeArray(data?.data?.topSignals ?? data?.topSignals ?? data?.data?.top_signals);
  const topRisks = safeArray(data?.data?.topRisks ?? data?.topRisks ?? data?.data?.top_risks);

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <DashboardIcon color="primary" />
        <Typography variant="h5">Vue d'ensemble</Typography>
        <FreshnessBadge stale={stale} />
      </Stack>

      {/* KPIs Cards */}
      {hasItems(kpis) && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {kpis.map((kpi, index) => (
            <Grid key={index} item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">
                    {safeString(kpi.label)}
                  </Typography>
                  <Typography variant="h5">
                    {safeString(kpi.value)}
                  </Typography>
                  {kpi.hint && (
                    <Typography variant="body2" color="text.secondary">
                      {kpi.hint}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Top Signals & Risks */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <TrendingUpIcon color="success" />
                <Typography variant="subtitle1">Top 3 Signaux</Typography>
              </Stack>
              {!hasItems(topSignals) ? (
                <Typography color="text.secondary">Aucun signal disponible</Typography>
              ) : (
                <Stack spacing={1}>
                  {topSignals.slice(0, 3).map((signal, index) => (
                    <Box key={index}>
                      <Typography variant="body2">
                        {safeString(signal.title ?? signal.name)}
                      </Typography>
                      {signal.score != null && (
                        <Typography variant="caption" color="text.secondary">
                          Score: {Number(signal.score).toFixed(2)}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <WarningIcon color="error" />
                <Typography variant="subtitle1">Top 3 Risques</Typography>
              </Stack>
              {!hasItems(topRisks) ? (
                <Typography color="text.secondary">Aucun risque détecté</Typography>
              ) : (
                <Stack spacing={1}>
                  {topRisks.slice(0, 3).map((risk, index) => (
                    <Box key={index}>
                      <Typography variant="body2">
                        {safeString(risk.title ?? risk.name)}
                      </Typography>
                      {risk.score != null && (
                        <Typography variant="caption" color="text.secondary">
                          Score: {Number(risk.score).toFixed(2)}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
```

### Checklist

- [ ] KPIs s'affichent en cartes
- [ ] Top 3 signaux/risques s'affichent
- [ ] Pas de crash si données vides
- [ ] Loading states corrects
- [ ] Console sans erreur

---

## 📋 ORDRE D'EXÉCUTION RECOMMANDÉ

1. **PRÉREQUIS** (1 agent, 20 pts) - Installation MUI + helpers
2. **FC-UI-NEWS-001** (80 pts) - URGENT, crash actuel
3. **FC-UI-FORECASTS-002** (100 pts) - Page critique
4. **FC-UI-DASHBOARD-003** (90 pts) - Page d'entrée
5. **FC-UI-MACRO-004** (70 pts) - Page Macro
6. **FC-UI-BACKTESTS-005** (80 pts) - Page Backtests
7. **FC-UI-JUDGE-006** (60 pts) - Page LLM Judge

**Total disponible** : 600+ points

---

## 🤝 COORDINATION

**IMPORTANT** :
- ✅ Créer lock file `.locks/<TASK-ID>.lock` avant de commencer
- ✅ Poster message dans AGENTS_MESSAGES.md quand terminé
- ✅ Créer screenshots dans `proofs/<TASK-ID>/<votre-handle>/`
- ✅ Demander review à CLAUDE-STABILITY-ARCHITECT-IRONMAN-42

---

**Questions ?** → Poster dans AGENTS_MESSAGES.md avec tag `[ASK]`
