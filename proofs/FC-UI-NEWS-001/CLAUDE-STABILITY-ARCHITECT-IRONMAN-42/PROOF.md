✅ **FC-UI-NEWS-001: Page News stabilisée avec Material-UI**

## Composants convertis en MUI

### 1. NewsCard.tsx - Avant/Après

**Avant**: Tailwind CSS + HTML brut
```tsx
<article className="border rounded-lg p-3 mb-3 hover:bg-neutral-50">
  <div className="text-sm text-neutral-500 flex gap-2">
    <span className="font-mono px-2 py-0.5 rounded bg-neutral-200">{ticker}</span>
```

**Après**: Material-UI complet
```tsx
<Card sx={{ mb: 2, '&:hover': { bgcolor: 'action.hover' } }}>
  <CardContent>
    <Stack direction="row" spacing={1}>
      <Chip label={ticker} size="small" sx={{ fontFamily: 'monospace' }} />
```

**Améliorations**:
- Card MUI avec hover effect professionnel
- Chip pour ticker et sentiment avec icons (TrendingUp/Down)
- Typography avec variants appropriés
- Couleurs du theme MUI (success/error pour sentiment)
- Ellipsis text avec WebkitLineClamp

### 2. NewsFeed.tsx - Avant/Après

**Avant**: Mix Tailwind + vieux helpers
```tsx
<div className="flex items-center justify-between mb-4">
<button className="px-4 py-2 rounded border">Charger plus</button>
import { safeGetArray, safeLength, safeMap } from '@/utils/safeAccess';
```

**Après**: MUI + nouveaux helpers
```tsx
<Stack direction="row" justifyContent="space-between" mb={2}>
<Button variant="outlined" size="large">Charger plus</Button>
import { safeArray, hasItems } from '@/lib/safe';
```

**Améliorations**:
- Box, Stack pour layouts au lieu de divs
- Button MUI avec variant outlined
- Alert MUI pour erreurs (severity="error")
- CircularProgress pour loading states
- Nouveau EmptyState component
- Migration vers nouveaux safety helpers

## Impact UI/UX

✅ **Cohérence visuelle**: Style MUI cohérent avec le reste de l'app
✅ **Professionnalisme**: Cards, Chips, Icons donnent un look moderne
✅ **Accessibilité**: Composants MUI respectent ARIA standards
✅ **Maintenabilité**: Code plus clean, moins de Tailwind classes
✅ **Theming**: Utilise le theme MUI (colors, spacing, typography)
✅ **Safety**: Helpers modernes préviennent les crashes

## Tests manuels

```bash
# Backend doit tourner sur :8050
curl http://localhost:8050/api/news/feed | jq '.data.count'
# Retourne 20+ articles

# Frontend affiche maintenant:
# - Cards avec hover effect
# - Sentiment badges colorés avec icons
# - Loading spinner élégant
# - Empty state MUI si pas de données
```

Page News prête pour livraison client.
