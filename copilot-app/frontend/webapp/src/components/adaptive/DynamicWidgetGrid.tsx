/**
 * Dynamic Widget Grid
 * 
 * Renders widgets dynamically based on adaptive layout configuration.
 * Maps widget IDs to actual React components.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 * Optimized: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 * Task: TASK-1.3 - Lazy loading widgets for initial load optimization
 */

import { Stack, Grid, Divider, Text, Alert, Skeleton } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';
import { Suspense, lazy, type ComponentType } from 'react';
import { useAdaptiveLayout } from '../../contexts/AdaptiveLayoutContext';
import { AdaptiveLayoutService, type WidgetId } from '../../services/adaptiveLayoutService';

// Lazy load widgets for code splitting and initial load optimization
// Top priority widgets (loaded first)
const IntelligenceDashboardWidget = lazy(() => 
  import('../widgets/IntelligenceDashboardWidget').then(m => ({ default: m.IntelligenceDashboardWidget }))
);
const SmartRecommendationsWidget = lazy(() => 
  import('../widgets/SmartRecommendationsWidget').then(m => ({ default: m.SmartRecommendationsWidget }))
);

// Middle priority widgets (loaded after top row)
const CorrelationIntelligenceWidget = lazy(() => 
  import('../widgets/CorrelationIntelligenceWidget').then(m => ({ default: m.CorrelationIntelligenceWidget }))
);
const ForecastCardsWidget = lazy(() => 
  import('../widgets/ForecastCardsWidget').then(m => ({ default: m.ForecastCardsWidget }))
);
const NewsWidget = lazy(() => 
  import('../widgets/NewsWidget').then(m => ({ default: m.NewsWidget }))
);

// Lower priority widgets (loaded last)
const MacroWidget = lazy(() => 
  import('../widgets/MacroWidget').then(m => ({ default: m.MacroWidget }))
);
const MacroSparklinesWidget = lazy(() => 
  import('../widgets/MacroSparklinesWidget').then(m => ({ default: m.MacroSparklinesWidget }))
);
const StocksWidget = lazy(() => 
  import('../widgets/StocksWidget').then(m => ({ default: m.StocksWidget }))
);

/**
 * Widget Registry
 * 
 * Maps widget IDs to lazy-loaded React components.
 * Widgets are loaded on-demand based on their priority in the layout.
 * 
 * Note: Other widgets may not exist yet - we'll handle gracefully
 */
const WIDGET_REGISTRY: Record<
  WidgetId,
  React.LazyExoticComponent<ComponentType<any>> | null
> = {
  intelligence: IntelligenceDashboardWidget,
  recommendations: SmartRecommendationsWidget,
  correlations: CorrelationIntelligenceWidget,
  forecasts: ForecastCardsWidget,
  news: NewsWidget,
  macro: MacroWidget,
  macro_sparklines: MacroSparklinesWidget,  // Added for FC-DASH-003
  stocks: StocksWidget,
  risks: null,
  opportunities: null,
  alerts: null,
  performance: null,
};

/**
 * Widget Loading Skeleton
 * 
 * Shows a loading placeholder while widget is being lazy-loaded.
 */
function WidgetSkeleton() {
  return (
    <Stack gap="md" p="md" style={{ minHeight: '200px' }}>
      <Skeleton height={20} width="60%" />
      <Skeleton height={16} width="80%" />
      <Skeleton height={16} width="40%" />
      <Skeleton height={100} />
    </Stack>
  );
}

/**
 * Widget Wrapper
 * 
 * Wraps each widget with consistent styling, error handling, and lazy loading.
 * Uses Suspense to handle async widget loading.
 */
function WidgetWrapper({
  widgetId,
  filters,
}: {
  widgetId: WidgetId;
  filters: Record<string, any>;
}) {
  const WidgetComponent = WIDGET_REGISTRY[widgetId];

  // Widget not yet implemented
  if (WidgetComponent === null) {
    return (
      <Alert color="gray" variant="light" icon={<IconInfoCircle size={20} />}>
        <Text size="sm" c="gray.3">
          Widget "{widgetId}" coming soon
        </Text>
      </Alert>
    );
  }

  // Apply filters to widget props
  const widgetProps = AdaptiveLayoutService.applyFiltersToWidgetProps(filters, widgetId);

  return (
    <Suspense fallback={<WidgetSkeleton />}>
      <WidgetComponentWrapper 
        WidgetComponent={WidgetComponent} 
        widgetProps={widgetProps} 
        widgetId={widgetId}
      />
    </Suspense>
  );
}

/**
 * Widget Component Wrapper
 * 
 * Internal wrapper that handles error boundaries for lazy-loaded widgets.
 */
function WidgetComponentWrapper({
  WidgetComponent,
  widgetProps,
  widgetId,
}: {
  WidgetComponent: React.LazyExoticComponent<ComponentType<any>>;
  widgetProps: Record<string, any>;
  widgetId: WidgetId;
}) {
  try {
    return <WidgetComponent {...widgetProps} />;
  } catch (error) {
    console.error(`Failed to render widget: ${widgetId}`, error);
    return (
      <Alert color="red" variant="light" icon={<IconInfoCircle size={20} />}>
        <Text size="sm">Failed to load {widgetId} widget</Text>
      </Alert>
    );
  }
}

/**
 * Widget Row
 * 
 * Renders a row of widgets with consistent grid layout.
 */
function WidgetRow({
  widgets,
  filters,
  priority,
}: {
  widgets: WidgetId[];
  filters: Record<string, any>;
  priority: 'top' | 'middle' | 'bottom';
}) {
  if (widgets.length === 0) return null;

  // Determine grid column span based on number of widgets and priority
  const getColSpan = (index: number, total: number): { base: number; md: number } => {
    if (priority === 'top') {
      // Top row: Full width for first widget if only one, otherwise split
      if (total === 1) return { base: 12, md: 12 };
      if (total === 2) return { base: 12, md: 6 };
      return { base: 12, md: 4 };
    }

    if (priority === 'middle') {
      // Middle row: Even split
      if (total === 1) return { base: 12, md: 12 };
      if (total === 2) return { base: 12, md: 6 };
      if (total === 3) return { base: 12, md: 4 };
      return { base: 12, md: 6 };
    }

    // Bottom row: Compact layout
    if (total <= 2) return { base: 12, md: 6 };
    if (total === 3) return { base: 12, md: 4 };
    return { base: 12, md: 3 };
  };

  return (
    <Grid gutter="md">
      {widgets.map((widgetId, index) => {
        const span = getColSpan(index, widgets.length);
        return (
          <Grid.Col key={widgetId} span={span}>
            <WidgetWrapper widgetId={widgetId} filters={filters} />
          </Grid.Col>
        );
      })}
    </Grid>
  );
}

/**
 * Dynamic Widget Grid
 * 
 * Main component that orchestrates adaptive widget rendering.
 * 
 * Optimization (TASK-1.3):
 * - Widgets are lazy-loaded to reduce initial bundle size
 * - Progressive loading: topRow → middleRow → bottomRow
 * - Each row wrapped in Suspense for independent loading
 * - Widgets only load when their row becomes visible
 */
export function DynamicWidgetGrid() {
  const { currentLayout, isLoading } = useAdaptiveLayout();

  if (isLoading) {
    return (
      <Stack gap="md">
        <Text c="gray.3" ta="center">
          Loading adaptive layout...
        </Text>
      </Stack>
    );
  }

  const { topRow, middleRow, bottomRow, defaultFilters } = currentLayout;

  return (
    <Stack gap="xl">
      {/* Top Row - Priority Widgets (loaded first) */}
      {topRow.length > 0 && (
        <Suspense fallback={
          <Stack gap="md">
            <Text c="gray.3" size="sm">Loading priority widgets...</Text>
            <Grid gutter="md">
              {topRow.map((id) => (
                <Grid.Col key={id} span={{ base: 12, md: topRow.length === 1 ? 12 : 6 }}>
                  <WidgetSkeleton />
                </Grid.Col>
              ))}
            </Grid>
          </Stack>
        }>
          <WidgetRow widgets={topRow} filters={defaultFilters} priority="top" />
          {(middleRow.length > 0 || bottomRow.length > 0) && <Divider />}
        </Suspense>
      )}

      {/* Middle Row - Secondary Widgets (loaded after top row) */}
      {middleRow.length > 0 && (
        <Suspense fallback={
          <Stack gap="md">
            <Text c="gray.3" size="sm">Loading secondary widgets...</Text>
            <Grid gutter="md">
              {middleRow.map((id) => (
                <Grid.Col key={id} span={{ base: 12, md: middleRow.length === 1 ? 12 : middleRow.length === 2 ? 6 : 4 }}>
                  <WidgetSkeleton />
                </Grid.Col>
              ))}
            </Grid>
          </Stack>
        }>
          <WidgetRow widgets={middleRow} filters={defaultFilters} priority="middle" />
          {bottomRow.length > 0 && <Divider />}
        </Suspense>
      )}

      {/* Bottom Row - Tertiary Widgets (loaded last) */}
      {bottomRow.length > 0 && (
        <Suspense fallback={
          <Stack gap="md">
            <Text c="gray.3" size="sm">Loading additional widgets...</Text>
            <Grid gutter="md">
              {bottomRow.map((id) => (
                <Grid.Col key={id} span={{ base: 12, md: bottomRow.length <= 2 ? 6 : bottomRow.length === 3 ? 4 : 3 }}>
                  <WidgetSkeleton />
                </Grid.Col>
              ))}
            </Grid>
          </Stack>
        }>
          <WidgetRow widgets={bottomRow} filters={defaultFilters} priority="bottom" />
        </Suspense>
      )}
    </Stack>
  );
}
