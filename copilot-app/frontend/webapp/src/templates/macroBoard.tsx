import { Stack } from '@mantine/core';
import { MacroBoardWidget } from '@/components/widgets/MacroBoardWidget';
import type { DashboardTemplate, TemplateRenderCtx } from './types';

function MacroBoardTemplate(_ctx: TemplateRenderCtx) {
  return (
    <Stack>
      <MacroBoardWidget />
    </Stack>
  );
}

export const macroBoardTemplate: DashboardTemplate = {
  slug: 'macro-board',
  label: 'Macro Board',
  description: 'Vue macro complète: CPI, VIX, courbe 10Y-2Y, chômage et signaux.',
  render: (ctx: TemplateRenderCtx) => <MacroBoardTemplate {...ctx} />,
};
