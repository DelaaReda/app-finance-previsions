import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';
import { BarList, Button, Card, Chip, DonutChart, Group, Heading, LoadingSpinner, RingProgress, SimpleGrid, Stack, Text } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import EmptyState from '@/components/ui/EmptyState';
import { safeArray } from '@/lib/safe';

interface ForecastRow {
  ticker?: string;
  asset_type?: string;
  horizon?: string;
  direction?: string;
  confidence?: number;
  expected_return?: number;
  features_used?: string[];
}

interface ForecastResponse {
  rows: ForecastRow[];
  freshness?: string;
  last_update?: string;
}

const HORIZON_OPTIONS = ['short', 'medium', 'long'];
const ASSET_TYPES = ['Equity', 'Index', 'Commodity', 'FX', 'Crypto'];

const fetchForecastsFromApi = async (): Promise<ForecastResponse> => {
  const res = await apiGet<ForecastResponse>('/forecasts', { asset_type: 'all', horizon: 'all', sort_by: 'score' });
  if (!res.ok || !res.data) {
    throw new Error(res.error || 'Erreur de chargement');
  }
  return res.data;
};

export default function Forecasts() {
  const [horizons, setHorizons] = useState<string[]>([]);
  const [assetTypes, setAssetTypes] = useState<string[]>([]);
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [minScore, setMinScore] = useState<number>(0);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['forecasts'],
    queryFn: fetchForecastsFromApi,
    staleTime: 60_000,
  });

  const rows = useMemo(() => {
    let current = safeArray(data?.rows ?? []);
    if (horizons.length > 0) {
      current = current.filter((row) => row.horizon && horizons.includes(row.horizon));
    }
    if (assetTypes.length > 0) {
      current = current.filter((row) => row.asset_type && assetTypes.includes(row.asset_type));
    }
    if (minConfidence > 0) {
      current = current.filter((row) => (row.confidence ?? 0) >= minConfidence / 100);
    }
    if (minScore > 0) {
      current = current.filter((row) => (row.expected_return ?? 0) >= minScore / 100);
    }
    return current;
  }, [data, horizons, assetTypes, minConfidence, minScore]);

  const positive = rows
    .filter((row) => (row.expected_return ?? 0) > 0)
    .sort((a, b) => (b.expected_return ?? 0) - (a.expected_return ?? 0))
    .slice(0, 8)
    .map((row) => ({
      name: `${row.ticker} • ${row.horizon}`,
      value: Math.round(((row.expected_return ?? 0) * 100) * 100) / 100,
    }));

  const negative = rows
    .filter((row) => (row.expected_return ?? 0) < 0)
    .sort((a, b) => (a.expected_return ?? 0) - (b.expected_return ?? 0))
    .slice(0, 8)
    .map((row) => ({
      name: `${row.ticker} • ${row.horizon}`,
      value: Math.round(Math.abs((row.expected_return ?? 0) * 100) * 100) / 100,
    }));

  const horizonDistribution = useMemo(() => {
    const counts: Record<string, number> = {};
    rows.forEach((row) => {
      const key = row.horizon ?? 'other';
      counts[key] = (counts[key] ?? 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [rows]);

  const averageConfidence = useMemo(() => {
    if (rows.length === 0) return 0;
    const sum = rows.reduce((acc, row) => acc + (row.confidence ?? 0), 0);
    return Math.round((sum / rows.length) * 100);
  }, [rows]);

  const freshness = data?.freshness ?? data?.last_update ?? undefined;

  return (
    <Stack gap="xl">
      <Heading order={2}>Prévisions de marché</Heading>

      <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
        <Card>
          <Stack align="center" gap="xs">
            <Text c="dimmed" fz="sm">Prévisions totales</Text>
            <Text fw={700} fz="xl">{data?.rows?.length ?? 0}</Text>
            <Text c="dimmed" fz="xs">{rows.length} affichées après filtres</Text>
          </Stack>
        </Card>
        <Card>
          <Stack align="center" gap="xs">
            <Text c="dimmed" fz="sm">Confiance moyenne</Text>
            <RingProgress
              size={120}
              thickness={12}
              sections={[{ value: averageConfidence, color: 'teal' }]}
              label={<Text fw={700}>{averageConfidence}%</Text>}
            />
          </Stack>
        </Card>
        <Card>
          <Stack align="center" gap="xs">
            <Text c="dimmed" fz="sm">Mise à jour</Text>
          <FreshnessBadge freshness={freshness} />
            <Button variant="light" onClick={() => refetch()} disabled={isLoading}>
              Rafraîchir
            </Button>
          </Stack>
        </Card>
      </SimpleGrid>

        <Card>
          <Stack gap="md">
            <Heading order={4}>Filtres</Heading>
          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
            <Stack gap="xs">
              <Text c="dimmed" fw={500} fz="xs">Horizons</Text>
              <Group gap="xs">
                {HORIZON_OPTIONS.map((option) => (
                  <Chip
                    key={option}
                    checked={horizons.includes(option)}
                    onChange={(checked) =>
                      setHorizons((prev) => (
                        checked ? [...prev, option] : prev.filter((v) => v !== option)
                      ))
                    }
                  >
                    {option}
                  </Chip>
                ))}
              </Group>
            </Stack>
            <Stack gap="xs">
              <Text c="dimmed" fw={500} fz="xs">Types d’actifs</Text>
              <Group gap="xs">
                {ASSET_TYPES.map((type) => (
                  <Chip
                    key={type}
                    checked={assetTypes.includes(type)}
                    onChange={(checked) =>
                      setAssetTypes((prev) => (
                        checked ? [...prev, type] : prev.filter((v) => v !== type)
                      ))
                    }
                  >
                    {type}
                  </Chip>
                ))}
              </Group>
            </Stack>
            <Stack gap="xs">
              <Text c="dimmed" fw={500} fz="xs">Seuils</Text>
              <Group gap="xs">
                <Chip checked={minConfidence > 0} onChange={(checked) => setMinConfidence(checked ? 70 : 0)}>
                  Confiance ≥ 70%
                </Chip>
                <Chip checked={minScore > 0} onChange={(checked) => setMinScore(checked ? 2 : 0)}>
                  Score ≥ 2%
                </Chip>
              </Group>
            </Stack>
          </SimpleGrid>
        </Stack>
      </Card>

      {isLoading && rows.length === 0 && (
        <Stack align="center" gap="sm">
          <LoadingSpinner />
          <Text c="dimmed">Chargement des prévisions…</Text>
        </Stack>
      )}

      {error && (
        <Card>
          <Text c="red">Erreur: {String(error)}</Text>
        </Card>
      )}

      {!isLoading && rows.length === 0 && !error && (
        <EmptyState title="Aucune prévision" subtitle="Essayez un autre horizon ou type d’actif." />
      )}

      {rows.length > 0 && (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl">
          <Card>
            <Stack gap="md">
              <Heading order={4}>Opportunités (retours positifs)</Heading>
              <BarList
                data={positive}
                valueFormatter={(value: number) => `${value.toFixed(2)}%`}
                color="teal"
              />
            </Stack>
          </Card>
          <Card>
            <Stack gap="md">
              <Heading order={4}>Risques (retours négatifs)</Heading>
              <BarList
                data={negative}
                valueFormatter={(value: number) => `-${value.toFixed(2)}%`}
                color="red"
              />
            </Stack>
          </Card>
        </SimpleGrid>
      )}

      {rows.length > 0 && (
        <Card>
          <Stack gap="md">
            <Heading order={4}>Répartition par horizon</Heading>
            <DonutChart
              data={horizonDistribution}
              category="value"
              index="name"
              colors={['indigo', 'teal', 'violet', 'cyan', 'slate']}
              valueFormatter={(value) => `${value} signaux`}
            />
          </Stack>
        </Card>
      )}
    </Stack>
  );
}
