/**
 * Layout Mode Toggle
 * 
 * Switch between automatic (regime-based) and manual layout modes.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 */

import { Group, Button, Text, Tooltip } from '@mantine/core';
import { IconAutomation, IconHandStop, IconRefresh } from '@tabler/icons-react';
import { useAdaptiveLayout } from '../../contexts/AdaptiveLayoutContext';

export function LayoutModeToggle() {
  const { isManualMode, toggleMode, refreshLayout } = useAdaptiveLayout();

  return (
    <Group gap="xs">
      <Tooltip
        label={
          isManualMode
            ? 'Switch to automatic layout (adapts to market regime)'
            : 'Switch to manual mode (fixed layout)'
        }
        position="bottom"
      >
        <Button
          variant={isManualMode ? 'light' : 'filled'}
          color={isManualMode ? 'gray' : 'blue'}
          size="xs"
          leftSection={isManualMode ? <IconHandStop size={16} /> : <IconAutomation size={16} />}
          onClick={toggleMode}
        >
          <Text size="xs">{isManualMode ? 'Manual' : 'Auto'}</Text>
        </Button>
      </Tooltip>

      {!isManualMode && (
        <Tooltip label="Refresh market context" position="bottom">
          <Button
            variant="subtle"
            size="xs"
            color="gray"
            onClick={refreshLayout}
            leftSection={<IconRefresh size={16} />}
          >
            <Text size="xs">Refresh</Text>
          </Button>
        </Tooltip>
      )}
    </Group>
  );
}
