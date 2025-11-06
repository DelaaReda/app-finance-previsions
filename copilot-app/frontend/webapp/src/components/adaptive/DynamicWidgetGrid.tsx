/**
 * Dynamic Widget Grid
 * 
 * Renders widgets dynamically based on adaptive layout configuration.
 * Maps widget IDs to actual React components.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 */

import { Stack, Grid, Divider, Text, Alert } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';
import { useAdaptiveLayout } from '../../contexts/AdaptiveLayoutContext';
import { AdaptiveLayoutService, type WidgetId } from '../../services/adaptiveLayoutService';

// Import widgets
import { IntelligenceDashboardWidget } from '../widgets/IntelligenceDashboardWidget';
import { SmartRecommendationsWidget } from '../widgets/SmartRecommendationsWidget';
import { CorrelationIntelligenceWidget } from '../widgets/CorrelationIntelligenceWidget';
import { ForecastCardsWidget } from '../widgets/ForecastCardsWidget';
// Note: Other widgets may not exist yet - we'll handle gracefully

/**
 * Widget Registry
 * 
 * Maps widget IDs to actual React components.
 * Add new widgets here as they're created.
 */
const WIDGET_REGISTRY: Record<
  WidgetId,
  React.ComponentType<any> | null
> = {
  intelligence: IntelligenceDashboardWidget,
  recommendations: SmartRecommendationsWidget,
  correlations: CorrelationIntelligenceWidget,
  forecasts: ForecastCardsWidget,
  news: null, // Placeholder - implement as needed
  macro: null,
  stocks: null,
  risks: null,
  opportunities: null,
  alerts: null,
  performance: null,
};

/**
 * Widget Wrapper
 * 
 * Wraps each widget with consistent styling and error handling.
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
        <Text size="sm" c="dimmed">
          Widget "{widgetId}" coming soon
        </Text>
      </Alert>
    );
  }

  // Apply filters to widget props
  const widgetProps = AdaptiveLayoutService.applyFiltersToWidgetProps(filters, widgetId);

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
 */
export function DynamicWidgetGrid() {
  const { currentLayout, isLoading } = useAdaptiveLayout();

  if (isLoading) {
    return (
      <Stack gap="md">
        <Text c="dimmed" ta="center">
          Loading adaptive layout...
        </Text>
      </Stack>
    );
  }

  const { topRow, middleRow, bottomRow, defaultFilters } = currentLayout;

  return (
    <Stack gap="xl">
      {/* Top Row - Priority Widgets */}
      {topRow.length > 0 && (
        <>
          <WidgetRow widgets={topRow} filters={defaultFilters} priority="top" />
          {(middleRow.length > 0 || bottomRow.length > 0) && <Divider />}
        </>
      )}

      {/* Middle Row - Secondary Widgets */}
      {middleRow.length > 0 && (
        <>
          <WidgetRow widgets={middleRow} filters={defaultFilters} priority="middle" />
          {bottomRow.length > 0 && <Divider />}
        </>
      )}

      {/* Bottom Row - Tertiary Widgets */}
      {bottomRow.length > 0 && (
        <WidgetRow widgets={bottomRow} filters={defaultFilters} priority="bottom" />
      )}
    </Stack>
  );
}
