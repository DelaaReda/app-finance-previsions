# Migration UI — Mantine-first avec Tremor & Tailwind (PO: NORA-11)

> Standardiser l’UI sur Mantine (v7) + Tremor (v3) + Tailwind utilitaire. Objectif: look propre, simple à générer par agents IA, sans crash.

---

## 0) Stack cible
- UI: Mantine (v7), icônes Tabler
- Charts / data: Tremor (v3)
- CSS utilitaires: Tailwind (layout/spacing)
- Thème: un seul thème Mantine (dark par défaut), tokens centralisés

## 1) Dépendances
```bash
# enlever MUI & co (si présents)
pnpm remove @mui/material @mui/icons-material @emotion/react @emotion/styled @mui/x-data-grid

# ajouter Mantine + icônes
pnpm add @mantine/core @mantine/hooks @mantine/notifications @tabler/icons-react

# Tremor + Tailwind v3
pnpm add @tremor/react
pnpm add -D tailwindcss@^3 postcss autoprefixer
```

## 2) Provider d’appli
`src/app/providers.tsx`
```tsx
import { ReactNode } from 'react';
import { MantineProvider, ColorSchemeScript, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

const theme = createTheme({
  fontFamily: 'Inter, ui-sans-serif, system-ui',
  defaultRadius: 'md',
  primaryColor: 'indigo',
  colors: {
    indigo: ['#edf2ff','#dbe4ff','#bac8ff','#91a7ff','#748ffc','#5c7cfa','#4c6ef5','#4263eb','#3b5bdb','#364fc7'],
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <>
      <ColorSchemeScript defaultColorScheme="auto" />
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <Notifications position="top-right" />
        {children}
      </MantineProvider>
    </>
  );
}
```

## 3) Wrappers UI (`src/ui/*`)
API simple et stable pour les agents IA; éviter imports directs Mantine.
```
src/ui/
  Button.tsx  Card.tsx  Badge.tsx  Tabs.tsx  Table.tsx
  Modal.tsx   Grid.tsx  Input.tsx  Select.tsx Loader.tsx Title.tsx
  index.ts
```
Exemple `src/ui/Button.tsx`:
```tsx
import { Button as MButton, ButtonProps as MProps } from '@mantine/core';
export type ButtonProps = MProps;
export function Button(props: ButtonProps) { return <MButton {...props} />; }
```

## 4) Helpers never‑empty
`src/utils/safe.ts`
```ts
export function ensureArray<T>(v: T[] | null | undefined): T[] { return Array.isArray(v) ? v : []; }
export function nn<T>(v: T | null | undefined, fallback: T): T { return v == null ? fallback : v; }
```

## 5) Pages à traiter (ordre)
- Dashboard: wrappers `@/ui`, Tremor pour KPI; Empty states.
- Macro: Cards + Loader Mantine; Tremor pour courbes; `ensureArray`.
- News: Mantine via `@/ui`; `ensureArray(data?.articles)`; Cards.
- Stocks: Table simple Mantine (tri minimal) au lieu de DataGrid lourd.
- Forecasts/Backtests: ensureArray + states + modales Mantine; Tremor pour graphs.
- Judge/Copilot: Layout Mantine (Grid, Card), inputs Mantine.

## 6) ESLint — Interdire MUI
`.eslintrc.cjs`
```js
module.exports = {
  rules: {
    'no-restricted-imports': ['error', {
      paths: [
        { name: '@mui/material', message: 'Utilise les wrappers src/ui/* (Mantine)' },
        { name: '@mui/icons-material', message: 'Utilise @tabler/icons-react' },
      ],
      patterns: ['@mui/*'],
    }],
  },
};
```

## 7) Backlog 48h
P0: retirer MUI; ajouter `src/ui/*`; corriger News & Forecasts avec `ensureArray` + states.
P1: Dashboard/Macro vers Mantine + Tremor; Stocks → table simple.
P2: Modales harmonisées; thème finance finalisé.

Chaque PR inclut screenshots & preuve sous `proofs/`.

