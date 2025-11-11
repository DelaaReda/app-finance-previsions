import { Stack } from '@mantine/core';
import { PerformanceMatrixWidget } from '@/components/widgets/PerformanceMatrixWidget';
import type { DashboardTemplate, TemplateRenderCtx } from './types';
import { ensureArray } from '@/lib/safe';

function PerformanceMatrixTemplate({ universe, themes }: TemplateRenderCtx) {
  const tickers = ensureArray(universe).length
    ? ensureArray(universe)
    : ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'META', 'AMZN', 'TSLA'];

  return (
    <Stack>
      <PerformanceMatrixWidget
        title="📈 Performance Matrix"
        universe={tickers}
        sectorOptions={[
          'Technology',
          'Energy',
          'Financials',
          'Healthcare',
          'Consumer',
          'Industrials',
          'Utilities',
          'Real Estate',
          'Materials',
          'Communication Services',
        ]}
        themeOptions={['growth', 'value', 'momentum', 'dividend', 'quality']}
        onSelectTicker={(ticker) => {
          window.location.href = `/stocks?t=${encodeURIComponent(ticker)}`;
        }}
      />
    </Stack>
  );
}

export const performanceMatrixTemplate: DashboardTemplate = {
  slug: 'performance-matrix',
  label: 'Performance Matrix',
  description: 'Heatmap multi-horizons des performances par ticker',
  render: (ctx: TemplateRenderCtx) => <PerformanceMatrixTemplate {...ctx} />,
};
