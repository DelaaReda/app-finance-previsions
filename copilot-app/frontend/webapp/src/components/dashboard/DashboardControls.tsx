import { Button, Chip, Group, MultiSelect, Select, Stack, Title } from '@mantine/core';
import type { DashboardContext } from '@/dashboards/types';

export function DashboardControls({
  value,
  onChange,
  onRefresh,
}: {
  value: DashboardContext;
  onChange: (next: DashboardContext) => void;
  onRefresh?: () => void;
}) {
  return (
    <Stack>
      <Title order={4}>Paramètres</Title>
      <Group justify="space-between" wrap="wrap">
        <Select
          label="Horizon"
          data={[
            { value: 'short', label: 'Court' },
            { value: 'medium', label: 'Moyen' },
            { value: 'long', label: 'Long' },
          ]}
          value={value.horizon}
          onChange={(next) => onChange({ ...value, horizon: (next as DashboardContext['horizon']) ?? value.horizon })}
          w={220}
        />
        <MultiSelect
          label="Univers"
          placeholder="Ex: SPY, QQQ, AAPL"
          data={Array.from(new Set(value.universe)).map((ticker) => ({ value: ticker, label: ticker }))}
          value={value.universe}
          searchable
          clearable
          onChange={(universe) => onChange({ ...value, universe })}
          w={360}
        />
        <MultiSelect
          label="Macro IDs"
          placeholder="CPIAUCSL, VIXCLS, …"
          data={Array.from(new Set(value.macroIds ?? [])).map((id) => ({ value: id, label: id }))}
          value={value.macroIds ?? []}
          searchable
          clearable
          onChange={(macroIds) => onChange({ ...value, macroIds })}
          w={360}
        />
      </Group>
      <Group>
        <Chip
          checked={Boolean(value.themes?.length)}
          onChange={() => onChange({ ...value, themes: value.themes?.length ? [] : ['growth'] })}
        >
          Thèmes (exemple: growth)
        </Chip>
        <Button variant="light" onClick={onRefresh}>
          Rafraîchir
        </Button>
      </Group>
    </Stack>
  );
}
