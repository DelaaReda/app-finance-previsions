import { Stack, Title, Text, Group, Alert } from '@mantine/core';
import { IconSparkles, IconInfoCircle } from '@tabler/icons-react';
import HealthBar from '@/components/widgets/HealthBar';
import { AdaptiveLayoutProvider } from '@/contexts/AdaptiveLayoutContext';
import { RegimeBadgeAdaptive } from '@/components/adaptive/RegimeBadgeAdaptive';
import { LayoutModeToggle } from '@/components/adaptive/LayoutModeToggle';
import { DynamicWidgetGrid } from '@/components/adaptive/DynamicWidgetGrid';

/**
 * Dashboard - Adaptive Layout
 * 
 * Dashboard that automatically adapts its layout based on market regime.
 * Surfaces the most relevant widgets first according to market context.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 */
function DashboardContent() {
  return (
    <Stack data-testid="dashboard-root" gap="lg">
      {/* Header */}
      <Stack gap="xs">
        <Group justify="space-between" align="flex-start">
          <div>
            <Group gap="xs" align="center">
              <IconSparkles size={28} color="#4169E1" />
              <Title order={2}>Adaptive Dashboard</Title>
            </Group>
            <Text c="dimmed" size="sm" mt={4}>
              Intelligent layout that adapts to market conditions in real-time
            </Text>
          </div>

          <Group gap="md" align="center">
            <RegimeBadgeAdaptive />
            <LayoutModeToggle />
          </Group>
        </Group>

        {/* Info Alert */}
        <Alert color="blue" variant="light" icon={<IconInfoCircle size={20} />}>
          <Text size="sm">
            <strong>Adaptive Mode Active:</strong> Dashboard layout automatically adjusts based on detected market regime. 
            Switch to Manual mode to lock the current layout.
          </Text>
        </Alert>
      </Stack>

      {/* System Health Bar */}
      <HealthBar />

      {/* Dynamic Widget Grid - Adapts to market context */}
      <DynamicWidgetGrid />
    </Stack>
  );
}

/**
 * Dashboard with Adaptive Layout Provider
 */
export default function Dashboard() {
  return (
    <AdaptiveLayoutProvider>
      <DashboardContent />
    </AdaptiveLayoutProvider>
  );
}
