import { Card, Title, Text } from '@/ui';
import { DonutChart, Legend } from '@tremor/react';
import { Alert, Group, Loader } from '@mantine/core';
import { ensureArray } from '@/lib/safe';
import { useStocksMeta } from '@/hooks/useStocksMeta';

type Props = {
  universe: string[];
  title?: string;
  description?: string;
  minSlicePct?: number; // regroupe les petits pays en “Other” si < %
  unknownLabel?: string; // libellé pour pays manquant
};

export function CountryDonutWidget({
  universe,
  title = 'Répartition par pays',
  description,
  minSlicePct = 3,
  unknownLabel = 'Unknown',
}: Props) {
  const { data, isLoading, error } = useStocksMeta(universe);

  if (isLoading) {
    return (
      <Card>
        <Group align="center" justify="center" p="md">
          <Loader size="sm" />
          <Text>Chargement des pays…</Text>
        </Group>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert color="red" title="Erreur">
          Impossible de récupérer les pays ({String(error)})
        </Alert>
      </Card>
    );
  }

  const items = ensureArray(data?.items);
  const perItemWeight = items.length > 0 ? 1 / items.length : 0;

  // Agrégation par pays (weight backend si dispo, sinon poids égal)
  const map = new Map<string, number>();
  for (const it of items) {
    const key = (it as any).country?.trim() || unknownLabel;
    const w =
      typeof it.weight === 'number' && isFinite(it.weight) && it.weight > 0
        ? it.weight
        : perItemWeight;
    map.set(key, (map.get(key) ?? 0) + w);
  }

  const total = Array.from(map.values()).reduce((a, b) => a + b, 0) || 1;

  const entries = Array.from(map.entries())
    .map(([name, value]) => ({ name, value, pct: (value / total) * 100 }))
    .sort((a, b) => b.value - a.value);

  // Regrouper les petites parts
  const major = entries.filter(e => e.pct >= minSlicePct);
  const minor = entries.filter(e => e.pct < minSlicePct);
  if (minor.length) {
    const otherValue = minor.reduce((acc, e) => acc + e.value, 0);
    major.push({ name: 'Other', value: otherValue, pct: (otherValue / total) * 100 });
  }

  const dataChart = major.map(({ name, value }) => ({ name, value }));

  if (dataChart.length === 0) {
    return (
      <Card>
        <Title order={4}>{title}</Title>
        {description && <Text c="dimmed" mt="xs">{description}</Text>}
        <Alert mt="md">Aucune donnée pays pour l’univers sélectionné.</Alert>
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
            data={dataChart}
            category="value"
            index="name"
            valueFormatter={(v: number) => `${(v / total * 100).toFixed(1)}%`}
            showTooltip
          />
        </div>
        <div>
          <Legend categories={dataChart.map(d => d.name)} className="max-w-sm" />
        </div>
      </div>
    </Card>
  );
}
