import type { DashboardTemplate } from '../types';

export const macroPulse: DashboardTemplate = {
  slug: 'macro-pulse',
  title: 'Macro Pulse',
  description: 'Focus macro (Inflation, Volatilité, Courbe des taux)',
  defaultContext: {
    horizon: 'short',
    universe: ['SPY', 'QQQ'],
    themes: [],
    macroIds: ['CPIAUCSL', 'VIXCLS'],
  },
  layout: [
    {
      id: 'macro-charts',
      title: 'Séries macro',
      widgets: [
        {
          id: 'macro-area',
          type: 'area',
          title: 'CPI vs VIX (aire)',
          colSpan: 12,
          height: 280,
          dataTestId: 'w-macro-area',
          data: { kind: 'macro', mapping: { index: 'date' } },
        },
      ],
    },
  ],
};
