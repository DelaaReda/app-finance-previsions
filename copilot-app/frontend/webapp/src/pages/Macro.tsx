import { Container, Stack } from '@mantine/core';
import { MacroBoardWidget } from '@/components/widgets/MacroBoardWidget';
import { MacroDrilldownWidget } from '@/components/widgets/MacroDrilldownWidget';

export default function MacroPage() {
  return (
    <Container size="xl" py="lg" data-testid="macro-board">
      <Stack gap="lg">
        <MacroBoardWidget />
        <MacroDrilldownWidget />
      </Stack>
    </Container>
  );
}
