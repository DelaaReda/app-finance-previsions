import { Stack, Title, Text, Group, Alert } from '@mantine/core';
import { IconSparkles, IconInfoCircle } from '@tabler/icons-react';
import { Suspense, lazy } from 'react';
import HealthBar from '@/components/widgets/HealthBar';
import { AdaptiveLayoutProvider } from '@/contexts/AdaptiveLayoutContext';

// Lazy load non-critical components for initial load optimization (TASK-1.3)
const RegimeBadgeAdaptive = lazy(() => 
  import('@/components/adaptive/RegimeBadgeAdaptive').then(m => ({ default: m.RegimeBadgeAdaptive }))
);
const LayoutModeToggle = lazy(() => 
  import('@/components/adaptive/LayoutModeToggle').then(m => ({ default: m.LayoutModeToggle }))
);
const DynamicWidgetGrid = lazy(() => 
  import('@/components/adaptive/DynamicWidgetGrid').then(m => ({ default: m.DynamicWidgetGrid }))
);

/**
 * Dashboard - Adaptive Layout
 * 
 * Dashboard that automatically adapts its layout based on market regime.
 * Surfaces the most relevant widgets first according to market context.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 * Optimized: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 * Task: TASK-1.3 - Lazy loading for initial load optimization
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

          <Suspense fallback={<div style={{ width: '200px', height: '40px' }} />}>
            <Group gap="md" align="center">
              <RegimeBadgeAdaptive />
              <LayoutModeToggle />
            </Group>
          </Suspense>
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

      {/* Dynamic Widget Grid - Adapts to market context (lazy-loaded) */}
      <Suspense fallback={
        <Stack gap="md" p="xl" align="center">
          <Text c="dimmed">Loading dashboard widgets...</Text>
        </Stack>
      }>
        <DynamicWidgetGrid />
      </Suspense>
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
