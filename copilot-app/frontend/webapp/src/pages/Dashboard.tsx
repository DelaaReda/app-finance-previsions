import { useMemo, useState } from 'react';
import { BarList, DonutChart, AreaChart } from '@tremor/react';
import { IconRefresh, IconArrowRight, IconMoodEmpty, IconNews } from '@tabler/icons-react';
import { Grid, Group, Stack, Title, Text, ActionIcon, SegmentedControl, MultiSelect, Badge, Skeleton, Tooltip, Anchor, Button, Divider, Paper } from '@mantine/core';

// UI wrappers (cards, titles, etc.) — if you expose them from '@/ui', keep using them
// Fallback to Mantine Card/Title if needed
import { Card as UICard } from '@/ui';

import FreshnessBadge from '@/components/ui/FreshnessBadge';
import { ensureArray, asString } from '@/lib/safe';

// Hooks (existants) — la signature exacte peut varier suivant ton repo
// On tolère (object) ou (arg1, arg2, ...). Adapte si besoin.
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
import { useForecasts } from '@/hooks/useForecasts';
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
import { useMacroSeries } from '@/hooks/useMacroSeries';
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
import { useNews } from '@/hooks/useNews';
import { ForecastMatrixWidget } from '@/components/widgets/ForecastMatrixWidget';
import { IntelligenceDashboardWidget } from '@/components/widgets/IntelligenceDashboardWidget';

// --------------------------------------------
// Helpers d'adaptation
// --------------------------------------------

type Horizon = 'short' | 'medium' | 'long';

function toSparkData(rows: Array<{ date?: string | number; value?: number }>, label: string) {
  return ensureArray(rows).map((row) => {
    const rawDate = row?.date;
    const date =
      typeof rawDate === 'number'
        ? new Date(rawDate).toISOString().slice(0, 10)
        : typeof rawDate === 'string'
        ? rawDate
        : '';
    return {
      date,
      [label]: Number(row?.value ?? 0),
    };
  });
}

// --------------------------------------------
// UI Components locaux (sparklines + tuiles)
// --------------------------------------------

function ForecastsCard({
  items,
  loading,
  onViewAll,
}: {
  items: any[];
  loading?: boolean;
  onViewAll?: () => void;
}) {
  const top5 = ensureArray(items).slice(0, 5);
  const barData = top5.map((f: any) => ({ name: asString(f?.symbol ?? f?.ticker, '—'), value: Number(f?.score ?? 0) }));
  const up = top5.filter((f: any) => (f?.dir ?? f?.direction) === 'up').length;
  const down = top5.filter((f: any) => (f?.dir ?? f?.direction) === 'down').length;

  return (
    <UICard data-testid="forecasts-card">
      <Group justify="space-between" align="center" mb="xs">
        <Title order={4}>Prévisions – Top 5</Title>
        <Group>
          <Badge variant="light" color="teal">Hausses: {up}</Badge>
          <Badge variant="light" color="red">Baisses: {down}</Badge>
          {onViewAll && (
            <Tooltip label="Voir toutes les prévisions">
              <ActionIcon variant="light" onClick={onViewAll} aria-label="Voir tout">
                <IconArrowRight size={18} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      </Group>

      {loading ? (
        <Stack>
          <Skeleton h={20} />
          <Skeleton h={20} />
          <Skeleton h={20} />
        </Stack>
      ) : barData.length ? (
        <BarList data={barData} showAnimation={true} valueFormatter={(value: number) => value.toFixed(2)} />
      ) : (
        <Group align="center" gap="sm">
          <IconMoodEmpty size={16} />
          <Text size="sm" c="dimmed">Aucune prévision disponible</Text>
        </Group>
      )}
    </UICard>
  );
}

function ForecastsDonut({ items }: { items: any[] }) {
  const counts = useMemo(() => {
    const arr = ensureArray(items);
    const up = arr.filter((f: any) => (f?.dir ?? f?.direction) === 'up').length;
    const down = arr.filter((f: any) => (f?.dir ?? f?.direction) === 'down').length;
    const flat = arr.filter((f: any) => (f?.dir ?? f?.direction) === 'flat').length;
    return [
      { name: 'Up', value: up },
      { name: 'Down', value: down },
      { name: 'Flat', value: flat },
    ].filter((d) => d.value > 0);
  }, [items]);

  return (
    <UICard data-testid="forecasts-donut">
      <Title order={5} mb="xs">Répartition directionnelle</Title>
      {counts.length === 0 ? (
        <Skeleton h={140} />
      ) : (
        <div style={{ height: 180 }}>
          <DonutChart
            data={counts}
            category="value"
            index="name"
            showLabel={true}
            colors={['teal', 'red', 'slate']}
            valueFormatter={(n: number) => `${n}`}
          />
        </div>
      )}
    </UICard>
  );
}

function NewsCard({ articles, loading }: { articles: any[]; loading?: boolean }) {
  const items = ensureArray(articles).slice(0, 6);
  return (
    <UICard data-testid="news-card">
      <Group justify="space-between" mb="xs">
        <Group gap={6}>
          <IconNews size={18} />
          <Title order={4}>News</Title>
        </Group>
        <Badge variant="light">{items.length} articles</Badge>
      </Group>
      {loading ? (
        <Stack>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} h={20} />
          ))}
        </Stack>
      ) : items.length ? (
        <Stack gap="sm">
          {items.map((n: any, idx: number) => (
            <Group key={idx} justify="space-between" align="center" wrap="nowrap">
              <Stack gap={2} style={{ minWidth: 0 }}>
                <Anchor href={n?.url} target="_blank" rel="noreferrer" lineClamp={1}>
                  {n?.title ?? 'Sans titre'}
                </Anchor>
                <Text size="xs" c="dimmed" lineClamp={1}>
                  {n?.source ?? '—'} · {n?.publishedAt ? new Date(n.publishedAt).toLocaleString('fr-FR') : '—'}
                </Text>
              </Stack>
              {n?.sentiment && (
                <Badge
                  variant="light"
                  color={n.sentiment === 'pos' ? 'teal' : n.sentiment === 'neg' ? 'red' : 'gray'}
                >
                  {n.sentiment}
                </Badge>
              )}
            </Group>
          ))}
        </Stack>
      ) : (
        <Group align="center" gap="sm">
          <IconMoodEmpty size={16} />
          <Text size="sm" c="dimmed">Aucune actualité</Text>
        </Group>
      )}
    </UICard>
  );
}

// --------------------------------------------
// DASHBOARD principal
// --------------------------------------------

export default function Dashboard() {
  // Filtres (propagés au hook de prévisions; les autres sections peuvent s'en servir plus tard)
  const [horizon, setHorizon] = useState<Horizon>('short');
  const [universe, setUniverse] = useState<string[]>(['SPY', 'QQQ']);
  const [themes, setThemes] = useState<string[]>([]);

  const forecastsQuery = useForecasts({ horizon, universe, themes });
  const forecasts = forecastsQuery.data ?? [];
  const fLoading = forecastsQuery.isLoading || forecastsQuery.isFetching;
  const fError = forecastsQuery.error as any;

  const macroQuery = useMacroSeries(['CPIAUCSL', 'VIXCLS']);
  const macroData = macroQuery.data ?? {};
  const mLoading = macroQuery.isLoading || macroQuery.isFetching;
  const cpiSeries = ensureArray((macroData as any)?.CPIAUCSL ?? (macroData as any)?.cpi ?? []);
  const vixSeries = ensureArray((macroData as any)?.VIXCLS ?? (macroData as any)?.vix ?? []);

  const newsQuery = useNews({ universe, limit: 6 });
  const articles = ensureArray(newsQuery.data);
  const nLoading = newsQuery.isLoading || newsQuery.isFetching;

  const refreshAll = () => {
    forecastsQuery.refetch();
    macroQuery.refetch();
    newsQuery.refetch();
  };

  const lastForecastUpdate = forecasts[0]?.updatedAt;
  const macroFreshness = cpiSeries.length
    ? cpiSeries[cpiSeries.length - 1]?.date
    : vixSeries.length
    ? vixSeries[vixSeries.length - 1]?.date
    : undefined;
  const newsFreshness = articles[0]?.publishedAt;

  return (
    <Stack data-testid="dashboard-root">
      {/* Header */}
      <Group justify="space-between" align="center">
        <Group>
          <Title order={2}>📊 Tableau de bord</Title>
          <FreshnessBadge freshness={lastForecastUpdate} />
        </Group>
        <Tooltip label="Actualiser toutes les sections">
          <ActionIcon size="lg" variant="light" onClick={refreshAll} aria-label="Actualiser">
            <IconRefresh size={18} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {/* Intelligence Dashboard Widget - Full Width */}
      <IntelligenceDashboardWidget />

      {/* Filtres */}
      <UICard data-testid="filters-card">
        <Stack>
          <Grid gutter="md" align="end">
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Text size="sm" c="dimmed" mb={6}>Horizon</Text>
              <SegmentedControl
                data-testid="filter-horizon"
                fullWidth
                value={horizon}
                onChange={(v) => setHorizon(v as Horizon)}
                data={[{ label: 'Court', value: 'short' }, { label: 'Moyen', value: 'medium' }, { label: 'Long', value: 'long' }]}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 5 }}>
              <Text size="sm" c="dimmed" mb={6}>Univers (tickers)</Text>
              <MultiSelect
                data-testid="filter-universe"
                searchable
                value={universe}
                onChange={setUniverse}
                data={[
                  { value: 'SPY', label: 'SPY' },
                  { value: 'QQQ', label: 'QQQ' },
                  { value: 'AAPL', label: 'AAPL' },
                  { value: 'MSFT', label: 'MSFT' },
                  { value: 'NVDA', label: 'NVDA' },
                  { value: 'META', label: 'META' },
                  { value: 'AMZN', label: 'AMZN' },
                  { value: 'TSLA', label: 'TSLA' },
                ]}
                placeholder="Sélectionne des tickers"
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 3 }}>
              <Text size="sm" c="dimmed" mb={6}>Thèmes</Text>
              <MultiSelect
                data-testid="filter-themes"
                value={themes}
                onChange={setThemes}
                data={[
                  { value: 'growth', label: 'Growth' },
                  { value: 'value', label: 'Value' },
                  { value: 'momentum', label: 'Momentum' },
                  { value: 'dividend', label: 'Dividend' },
                  { value: 'quality', label: 'Quality' },
                ]}
                placeholder="(optionnel)"
              />
            </Grid.Col>
          </Grid>
        </Stack>
      </UICard>

      {/* Contenu principal */}
      <Grid gutter="md">
        {/* Colonne gauche */}
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <Grid gutter="md">
            <Grid.Col span={{ base: 12, md: 7 }}>
              <ForecastsCard
                items={forecasts}
                loading={fLoading}
                onViewAll={() => (window.location.href = '/forecasts')}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 5 }}>
              <ForecastsDonut items={forecasts} />
            </Grid.Col>
          </Grid>

          <Divider my="md" label="Macro" labelPosition="center" />

          <Grid gutter="md">
            <Grid.Col span={{ base: 12, md: 6 }}>
              {mLoading ? (
                <Skeleton h={180} radius="md" />
              ) : (
                <div style={{ height: 180 }}>
                  <AreaChart
                    data={toSparkData(cpiSeries, 'CPI')}
                    index="date"
                    categories={['CPI']}
                    colors={['indigo']}
                    showLegend={false}
                    showGridLines={false}
                    yAxisWidth={36}
                  />
                </div>
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              {mLoading ? (
                <Skeleton h={180} radius="md" />
              ) : (
                <div style={{ height: 180 }}>
                  <AreaChart
                    data={toSparkData(vixSeries, 'VIX')}
                    index="date"
                    categories={['VIX']}
                    colors={['rose']}
                    showLegend={false}
                    showGridLines={false}
                    yAxisWidth={36}
                  />
                </div>
              )}
            </Grid.Col>
          </Grid>

          <ForecastMatrixWidget
            key={`forecast-matrix-${universe.join(',')}`}
            defaultUniverse={universe}
            defaultHorizons={['1m', '3m', '6m', '12m']}
          />
        </Grid.Col>

        {/* Colonne droite */}
        <Grid.Col span={{ base: 12, lg: 4 }}>
          <UICard mb="sm">
            <Group justify="space-between" align="center">
              <Text size="sm" c="dimmed">Fraîcheur des données</Text>
            </Group>
            <Stack gap={8} mt={8}>
              <Group justify="space-between"><Text size="sm">Prévisions</Text><FreshnessBadge freshness={lastForecastUpdate} /></Group>
              <Group justify="space-between"><Text size="sm">Macro</Text><FreshnessBadge freshness={macroFreshness} /></Group>
              <Group justify="space-between"><Text size="sm">News</Text><FreshnessBadge freshness={newsFreshness} /></Group>
            </Stack>
          </UICard>

          <NewsCard articles={articles} loading={nLoading} />

          <Paper withBorder p="sm" radius="md" mt="sm">
            <Stack gap={8}>
              <Text size="sm" c="dimmed">Actions rapides</Text>
              <Button variant="light" onClick={() => (window.location.href = '/backtests')}>
                Ouvrir Backtests
              </Button>
              <Button variant="light" onClick={() => (window.location.href = '/news')}>
                Voir toutes les news
              </Button>
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      {/* États globaux d'erreur (optionnels) */}
      {(fError || macroQuery.error || newsQuery.error) && (
        <UICard>
          <Title order={5}>Erreurs</Title>
          <Text size="sm" c="dimmed">{String(fError || macroQuery.error || newsQuery.error)}</Text>
        </UICard>
      )}
    </Stack>
  );
}
