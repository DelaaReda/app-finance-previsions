import { Container, Stack } from '@mantine/core';
import { IconChartBar } from '@tabler/icons-react';
import { MacroBoardWidget } from '@/components/widgets/MacroBoardWidget';
import { MacroDrilldownWidget } from '@/components/widgets/MacroDrilldownWidget';
import PageHeader from '@/components/layout/PageHeader';

export default function MacroPage() {
  return (
    <Container size="xl" py="xl" data-testid="macro-board">
      <PageHeader
        title="Indicateurs Macroéconomiques"
        icon={<IconChartBar size={28} />}
        description="Données FRED (CPI, VIX, Yield Curve, Employment) avec visualisations interactives"
        badge={{ label: 'Live', color: 'green' }}
      />
      <Stack gap="xl" mt="xl">
        <MacroBoardWidget />
        <MacroDrilldownWidget />
      </Stack>
    </Container>
  );
}
