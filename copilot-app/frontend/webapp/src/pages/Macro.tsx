import { useQuery } from '@tanstack/react-query';
import { macroService } from '@/services/macro.service';
import { BarList, Card, Heading, LoadingSpinner, RingProgress, SimpleGrid, Stack, Text } from '@/ui';

const METRICS = [
  { key: 'inflation_yoy', label: 'Inflation (YoY)', max: 10, description: 'Inflation annuelle' },
  { key: 'yield_curve_slope', label: 'Yield Curve (10Y-2Y)', max: 2, description: 'Pente courbe des taux' },
  { key: 'unemployment', label: 'Chômage', max: 15, description: 'Taux de chômage' },
  { key: 'recession_prob', label: 'Proba récession', max: 1, description: 'Probabilité de récession (12m)' },
];

const RISK_KEYS = ['recession_prob', 'inflation_yoy', 'unemployment'];

export default function Macro() {
  const { data, isLoading } = useQuery({
    queryKey: ['macro-snapshot'],
    queryFn: async () => {
      const resp = await macroService.getSnapshot();
      if (!resp.ok) throw new Error(resp.error || 'Impossible de récupérer les données macro');
      return resp.data ?? {};
    },
    staleTime: 60_000,
  });

  const snapshot = data ?? {};

  if (isLoading) {
    return (
      <Stack align="center" gap="sm">
        <LoadingSpinner />
        <Text c="dimmed">Chargement des indicateurs macro…</Text>
      </Stack>
    );
  }

  const rings = METRICS.map((metric) => {
    const rawValue = Number(snapshot[metric.key] ?? 0);
    const normalized = Math.max(0, Math.min(1, Math.abs(rawValue) / metric.max));
    const percent = Math.round(normalized * 100);
    return {
      metric,
      rawValue,
      percent,
      color: metric.key === 'recession_prob' ? (percent > 40 ? 'red' : 'teal') : percent > 60 ? 'orange' : 'teal',
    };
  });

  const riskList = RISK_KEYS.map((key) => ({
    name: METRICS.find((m) => m.key === key)?.label ?? key,
    value: Number(snapshot[key] ?? 0) * (key === 'recession_prob' ? 100 : 1),
  })).sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  return (
    <Stack gap="xl">
      <Heading order={2}>Pulse Macroéconomique</Heading>

      <SimpleGrid cols={{ base: 1, sm: 2, xl: 4 }} spacing="lg">
        {rings.map(({ metric, rawValue, percent, color }) => (
          <Card key={metric.key} padding="xl" radius="lg">
            <Stack align="center" gap="sm">
              <RingProgress
                size={140}
                thickness={12}
                roundCaps
                sections={[{ value: percent, color }]}
                label={<Text fw={700} fz="xl">{percent}%</Text>}
              />
              <Stack gap={2} align="center">
                <Text fw={600}>{metric.label}</Text>
                <Text c="dimmed" fz="sm">{metric.description}</Text>
                <Text fz="xs" c="slate.5">Valeur actuelle : {rawValue.toFixed(2)}</Text>
              </Stack>
            </Stack>
          </Card>
        ))}
      </SimpleGrid>

      <Card radius="lg" padding="xl" shadow="md">
        <Stack gap="md">
          <Heading order={4}>Stress radar macro</Heading>
          <Text c="dimmed" fz="sm">
            Pondération relative des facteurs de risque détectés cette semaine.
          </Text>
          <BarList
            data={riskList.map((item) => ({
              name: item.name,
              value: Number(item.value.toFixed(2)),
            }))}
            color="indigo"
          />
        </Stack>
      </Card>
    </Stack>
  );
}
