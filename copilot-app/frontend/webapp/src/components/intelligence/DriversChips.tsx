import { Group, Chip } from '@mantine/core';

interface DriversChipsProps {
  drivers: string[];
}

/**
 * DriversChips Component
 * 
 * Displays key market drivers as compact chips
 * Quick visual understanding of main market forces
 * 
 * @param drivers - Array of driver strings
 */
export function DriversChips({ drivers }: DriversChipsProps) {
  if (!drivers || drivers.length === 0) {
    return null;
  }

  return (
    <Group gap="xs">
      {drivers.map((driver, index) => (
        <Chip
          key={`${driver}-${index}`}
          size="sm"
          variant="filled"
          color="blue"
          checked={false}
          styles={{
            label: {
              cursor: 'default',
              fontSize: '0.875rem',
            },
          }}
        >
          {driver}
        </Chip>
      ))}
    </Group>
  );
}
