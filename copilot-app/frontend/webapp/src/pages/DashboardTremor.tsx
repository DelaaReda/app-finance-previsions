// Dashboard VIVANT - Mantine + Tremor avec graphiques partout
// Migration from MUI to Mantine/Tremor for better UX

import { Container, Title, Text, Grid, Card, Badge, Group, Stack, Loader, Alert, Box } from '@mantine/core'
import { BarList, Metric, DonutChart } from '@tremor/react'
import { IconTrendingUp, IconTrendingDown, IconActivity, IconAlertCircle } from '@tabler/icons-react'
import { safeArray } from '@/lib/safe'
import { useForecasts } from '@/hooks/useForecasts'
import { useMacroSnapshot } from '@/hooks/useMacroData'
import { useNewsCompat } from '@/hooks/useNewsCompat'

type CompositeSignal = {
  ticker: string
  composite_score: number
  macro_score: number
  technical_score: number
  news_score: number
  reason: string
  confidence: number
}

type DashboardData = {
  last_forecast_dt?: string | null
  forecasts_count?: number
  tickers?: number
  horizons?: string[]
  last_macro_dt?: string | null
  last_quality_dt?: string | null
  filtered_signals?: CompositeSignal[]
  filtered_risks?: CompositeSignal[]
  filtered_ticker_count?: number
  generated_at?: string
}

export default function DashboardTremor() {
  const includeSignals = true;

  // Use existing hooks and compose a lightweight dashboard view
  const forecastsQ = useForecasts({ horizon: 'short', universe: [] });
  const macroQ = useMacroSnapshot();
  const newsQ = useNewsCompat();

  const isLoading = forecastsQ.isLoading || macroQ.isLoading || newsQ.loading;
  const error = (forecastsQ.error ?? macroQ.error ?? (newsQ.error as any)) as any;

  // Compose lightweight data
  const signals = safeArray(forecastsQ.data).slice(0, 5).map((f: any) => ({
    ticker: f.symbol ?? f.ticker ?? 'N/A',
    composite_score: f.score ?? f.confidence ?? 0,
    macro_score: 0,
    technical_score: 0,
    news_score: 0,
    reason: f.reason ?? '',
    confidence: f.confidence ?? f.score ?? 0,
  }));

  const risks = [] as any[];

  const data = {
    last_forecast_dt: undefined,
    forecasts_count: safeArray(forecastsQ.data).length,
    tickers: undefined,
    horizons: [],
    last_macro_dt: (macroQ.data as any)?.last_update ?? undefined,
    last_quality_dt: undefined,
    filtered_signals: signals,
    filtered_risks: risks,
    filtered_ticker_count: undefined,
    generated_at: new Date().toISOString(),
  } as DashboardData

  // Transform pour Tremor BarList
  const signalsData = signals.map(s => ({
    name: s.ticker,
    value: Math.round(s.composite_score * 100), // 0-100
    href: `/ticker/${s.ticker}`,
    icon: function Icon() {
      return <IconTrendingUp size={16} color="green" />
    },
  }))

  const risksData = risks.map(r => ({
    name: r.ticker,
    value: Math.abs(Math.round(r.composite_score * 100)), // 0-100
    href: `/ticker/${r.ticker}`,
    icon: function Icon() {
      return <IconTrendingDown size={16} color="red" />
    },
  }))

  // DonutChart pour horizons
  const horizonsData = (data?.horizons || []).map(h => ({
    name: h,
    value: 1, // Equal distribution pour l'instant
  }))

  if (error) {
    return (
      <Container size="xl" py="xl">
        <Alert color="red" title="Erreur" icon={<IconAlertCircle size={16} />}>
          Impossible de charger le dashboard: {String(error)}
        </Alert>
      </Container>
    )
  }

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        {/* Header */}
        <div>
          <Title order={1} fw={700} size="h1">
            Dashboard - Vue d'ensemble
          </Title>
          <Text c="dimmed" size="sm">
            Analyse complète des prévisions, signaux et risques de marché
          </Text>
        </div>

        {/* Loading */}
        {isLoading && (
          <Box style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
            <Loader size="lg" />
          </Box>
        )}

        {/* KPIs - Tremor Metrics */}
        {!isLoading && data && (
          <>
            <Grid gutter="lg">
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between" align="center">
                      <Text size="sm" c="dimmed" fw={500}>
                        Prévisions
                      </Text>
                      <IconActivity size={20} color="blue" />
                    </Group>
                    <Metric>{data.forecasts_count ?? 0}</Metric>
                    <Text size="xs" c="dimmed">
                      Dernière: {data.last_forecast_dt || '—'}
                    </Text>
                  </Stack>
                </Card>
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between" align="center">
                      <Text size="sm" c="dimmed" fw={500}>
                        Tickers suivis
                      </Text>
                      <IconTrendingUp size={20} color="green" />
                    </Group>
                    <Metric>{data.tickers ?? 0}</Metric>
                    <Text size="xs" c="dimmed">
                      Univers analysé
                    </Text>
                  </Stack>
                </Card>
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between" align="center">
                      <Text size="sm" c="dimmed" fw={500}>
                        Signaux détectés
                      </Text>
                      <IconTrendingUp size={20} color="teal" />
                    </Group>
                    <Metric>{signals.length}</Metric>
                    <Text size="xs" c="dimmed">
                      Opportunités
                    </Text>
                  </Stack>
                </Card>
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between" align="center">
                      <Text size="sm" c="dimmed" fw={500}>
                        Risques
                      </Text>
                      <IconTrendingDown size={20} color="red" />
                    </Group>
                    <Metric>{risks.length}</Metric>
                    <Text size="xs" c="dimmed">
                      Points d'attention
                    </Text>
                  </Stack>
                </Card>
              </Grid.Col>
            </Grid>

            {/* Signals & Risks - Tremor BarList */}
            <Grid gutter="lg">
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Stack gap="md">
                    <Group justify="space-between">
                      <div>
                        <Text fw={600} size="lg">
                          🚀 Top Signaux
                        </Text>
                        <Text size="xs" c="dimmed">
                          Opportunités d'investissement
                        </Text>
                      </div>
                      <Badge color="green" variant="light" size="lg">
                        {signals.length} actifs
                      </Badge>
                    </Group>

                    {signals.length > 0 ? (
                      <BarList
                        data={signalsData}
                        color="emerald"
                        showAnimation
                      />
                    ) : (
                      <Text c="dimmed" ta="center" py="xl">
                        Aucun signal détecté
                      </Text>
                    )}
                  </Stack>
                </Card>
              </Grid.Col>

              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Stack gap="md">
                    <Group justify="space-between">
                      <div>
                        <Text fw={600} size="lg">
                          ⚠️ Top Risques
                        </Text>
                        <Text size="xs" c="dimmed">
                          Points d'attention prioritaires
                        </Text>
                      </div>
                      <Badge color="red" variant="light" size="lg">
                        {risks.length} actifs
                      </Badge>
                    </Group>

                    {risks.length > 0 ? (
                      <BarList
                        data={risksData}
                        color="red"
                        showAnimation
                      />
                    ) : (
                      <Text c="dimmed" ta="center" py="xl">
                        Aucun risque majeur détecté
                      </Text>
                    )}
                  </Stack>
                </Card>
              </Grid.Col>
            </Grid>

            {/* Horizons Distribution - Tremor DonutChart */}
            {horizonsData.length > 0 && (
              <Grid gutter="lg">
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Card shadow="sm" padding="lg" radius="md" withBorder>
                    <Stack gap="md">
                      <div>
                        <Text fw={600} size="lg">
                          📊 Distribution Horizons
                        </Text>
                        <Text size="xs" c="dimmed">
                          Répartition des prévisions par horizon temporel
                        </Text>
                      </div>

                      <DonutChart
                        data={horizonsData}
                        category="value"
                        index="name"
                        colors={['blue', 'cyan', 'indigo']}
                        showAnimation
                        showLabel
                      />

                      <Group gap="xs" justify="center">
                        {data.horizons?.map((h, i) => (
                          <Badge key={i} variant="light" size="sm">
                            {h}
                          </Badge>
                        ))}
                      </Group>
                    </Stack>
                  </Card>
                </Grid.Col>

                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Card shadow="sm" padding="lg" radius="md" withBorder>
                    <Stack gap="md">
                      <div>
                        <Text fw={600} size="lg">
                          ℹ️ Informations
                        </Text>
                        <Text size="xs" c="dimmed">
                          Métadonnées du dashboard
                        </Text>
                      </div>

                      <Stack gap="xs">
                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Univers analysé:
                          </Text>
                          <Text size="sm" fw={500}>
                            {data.filtered_ticker_count ?? data.tickers ?? 0} tickers
                          </Text>
                        </Group>

                        {data.generated_at && (
                          <Group justify="space-between">
                            <Text size="sm" c="dimmed">
                              Dernière mise à jour:
                            </Text>
                            <Text size="sm" fw={500}>
                              {new Date(data.generated_at).toLocaleString('fr-FR')}
                            </Text>
                          </Group>
                        )}

                        <Group justify="space-between">
                          <Text size="sm" c="dimmed">
                            Mode:
                          </Text>
                          <Badge color={includeSignals ? 'green' : 'gray'} variant="light">
                            {includeSignals ? 'Détaillé' : 'Rapide'}
                          </Badge>
                        </Group>
                      </Stack>
                    </Stack>
                  </Card>
                </Grid.Col>
              </Grid>
            )}
          </>
        )}
      </Stack>
    </Container>
  )
}
