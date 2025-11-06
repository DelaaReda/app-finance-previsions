import { Card, Title, Text } from '@/ui';
import { DonutChart, Legend } from '@tremor/react';
import { Alert, Group, Loader } from '@mantine/core';
import { ensureArray } from '@/lib/safe';
import { useStocksMeta } from '@/hooks/useStocksMeta';

type DonutWidgetProps = {
  universe: string[];
  title?: string;
  description?: string;
  minSlicePct?: number; // regroupe les petits secteurs dans “Other” si < %
};

export function DonutWidget({
  universe,
  title = 'Répartition sectorielle',
  description,
  minSlicePct = 3,
}: DonutWidgetProps) {
  const { data, isLoading, error } = useStocksMeta(universe);

  if (isLoading) {
    return (
      <Card>
        <Group align="center" justify="center" p="md">
          <Loader size="sm" />
          <Text>Chargement des secteurs…</Text>
        </Group>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert color="red" title="Erreur">
          Impossible de récupérer les secteurs ({String(error)})
        </Alert>
      </Card>
    );
  }

  const items = ensureArray(data?.items);
  // Regroupement par secteur, poids = weight sinon 1 / ticker
  const rawMap = new Map<string, number>();
  const perItemWeight = items.length > 0 ? 1 / items.length : 0;

  for (const it of items) {
    const k = it.sector?.trim() || 'Unknown';
    const w = typeof it.weight === 'number' ? it.weight : perItemWeight;
    rawMap.set(k, (rawMap.get(k) ?? 0) + (w > 0 ? w : 0));
  }

  const sum = Array.from(rawMap.values()).reduce((a, b) => a + b, 0) || 1;
  const entries = Array.from(rawMap.entries())
    .map(([name, value]) => ({ name, value, pct: (value / sum) * 100 }))
    .sort((a, b) => b.value - a.value);

  const major = entries.filter(e => e.pct >= minSlicePct);
  const minor = entries.filter(e => e.pct < minSlicePct);
  if (minor.length) {
    const other = minor.reduce((acc, e) => acc + e.value, 0);
    major.push({ name: 'Other', value: other, pct: (other / sum) * 100 });
  }

  const chartData = major.map(({ name, value }) => ({ name, value }));

  if (chartData.length === 0) {
    return (
      <Card>
        <Title order={4}>{title}</Title>
        {description && <Text c="dimmed" mt="xs">{description}</Text>}
        <Alert mt="md">Aucune donnée secteur pour l’univers sélectionné.</Alert>
      </Card>
    );
  }

  return (
    <Card>
      <Title order={4}>{title}</Title>
      {description && <Text c="dimmed" mt="xs">{description}</Text>}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2">
          <DonutChart
            data={chartData}
            category="value"
            index="name"
            valueFormatter={(n: number) => `${(n / sum * 100).toFixed(1)}%`}
            showTooltip
          />
        </div>
        <div>
          <Legend
            categories={chartData.map(d => d.name)}
            className="max-w-sm"
          />
        </div>
      </div>
    </Card>
  );
}
