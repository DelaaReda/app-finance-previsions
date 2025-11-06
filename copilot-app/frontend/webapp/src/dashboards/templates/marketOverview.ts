import type { DashboardTemplate } from '../types';

export const marketOverview: DashboardTemplate = {
  slug: 'market-overview',
  title: 'Market Overview',
  description: 'Aperçu du marché: CPI/VIX, Top prévisions, News récentes',
  defaultContext: {
    horizon: 'short',
    universe: ['SPY', 'QQQ'],
    themes: [],
    macroIds: ['CPIAUCSL', 'VIXCLS'],
  },
  layout: [
    {
      id: 'macro-spark',
      title: 'Macro Pulse',
      widgets: [
        {
          id: 'macro-line',
          type: 'line',
          title: 'CPI & VIX',
          colSpan: 12,
          height: 260,
          dataTestId: 'w-macro-line',
          data: {
            kind: 'macro',
            params: {},
            mapping: { index: 'date' },
          },
        },
      ],
    },
    {
      id: 'kpis',
      title: 'KPIs',
      widgets: [
        {
          id: 'metric-count',
          type: 'metric',
          title: 'Prévisions disponibles',
          colSpan: 3,
          dataTestId: 'w-forecast-count',
          data: { kind: 'forecasts', params: { metric: 'count' } },
        },
        {
          id: 'metric-avg',
          type: 'metric',
          title: 'Score moyen',
          colSpan: 3,
          dataTestId: 'w-forecast-avg',
          data: { kind: 'forecasts', params: { metric: 'avgScore' } },
        },
        {
          id: 'metric-up',
          type: 'metric',
          title: 'Bias haussier',
          colSpan: 3,
          dataTestId: 'w-forecast-up',
          data: { kind: 'forecasts', params: { metric: 'pctUp' } },
        },
        {
          id: 'metric-last',
          type: 'metric',
          title: 'Dernière MAJ',
          colSpan: 3,
          dataTestId: 'w-forecast-updated',
          data: { kind: 'forecasts', params: { metric: 'lastUpdate' } },
        },
      ],
    },
    {
      id: 'toplists',
      title: 'Top listes',
      widgets: [
        {
          id: 'barlist-top',
          type: 'barlist',
          title: 'Top par score',
          colSpan: 6,
          height: 320,
          dataTestId: 'w-forecast-top',
          data: { kind: 'forecasts', params: { orderBy: 'score', limit: 10 } },
        },
        {
          id: 'barlist-er',
          type: 'barlist',
          title: 'Top Expected Return',
          colSpan: 6,
          height: 320,
          dataTestId: 'w-forecast-er',
          data: { kind: 'forecasts', params: { orderBy: 'expectedReturn', limit: 10 } },
        },
      ],
    },
    {
      id: 'news',
      title: 'News',
      widgets: [
        {
          id: 'news-table',
          type: 'table',
          title: 'Dernières actualités',
          colSpan: 12,
          height: 360,
          dataTestId: 'w-news-table',
          data: { kind: 'news', params: { limit: 8 } },
        },
      ],
    },
  ],
};
