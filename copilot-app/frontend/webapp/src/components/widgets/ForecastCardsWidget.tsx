import { useState, useMemo } from 'react';
import { Grid, Group, Alert, SegmentedControl, Tooltip, ActionIcon } from '@mantine/core';
import { Card, Title, Text, Button, Badge } from '@/ui';
import { RingProgress } from '@mantine/core';
import { BadgeDelta } from '@tremor/react';
import { useForecasts } from '@/hooks/useForecasts';
import type { Horizon as ForecastHorizon } from '@/types/forecast';

type Props = {
  universe: string[];
  initialHorizon?: ForecastHorizon;
  limit?: number;
  title?: string;
  onSelectTicker?: (ticker: string) => void;
  onOpenDetails?: (ticker: string) => void;
};

function dirToDelta(d: 'up' | 'down' | 'flat') {
  if (d === 'up') return 'increase';
  if (d === 'down') return 'decrease';
  return 'unchanged';
}
function dirToBadge(d: 'up' | 'down' | 'flat') {
  if (d === 'up') return { label: 'Haussier', color: 'green' as const };
  if (d === 'down') return { label: 'Baissier', color: 'red' as const };
  return { label: 'Neutre', color: 'gray' as const };
}
function fmtPct(x: number) {
  const sign = x > 0 ? '+' : x < 0 ? '−' : '';
  return `${sign}${Math.abs(x).toFixed(2)}%`;
}

export function ForecastCardsWidget({
  universe,
  initialHorizon = 'short',
  limit = 12,
  title = 'Prévisions (cartes)',
  onSelectTicker,
  onOpenDetails,
}: Props) {
  const [hz, setHz] = useState<ForecastHorizon>(initialHorizon);
  const { data, isLoading, error, refetch, isFetching } = useForecasts({ horizon: hz, universe });

  const items = useMemo(() => {
    const arr = (data ?? []).slice();
    arr.sort((a, b) => b.score - a.score || ((b.confidence ?? 0) - (a.confidence ?? 0)));
    return arr.slice(0, limit);
  }, [data, limit]);

  const exportCsv = () => {
    const lines: string[] = [];
    lines.push('symbol,horizon,score,confidence,direction,expected_return_pct,updated_at');
    (data ?? []).forEach((f) => {
      lines.push([
        f.symbol,
        f.horizon,
        f.score,
        f.confidence ?? 0,
        f.direction,
        ((f.expectedReturn ?? 0)).toFixed(4),
        f.updatedAt ?? '',
      ].join(','));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `forecasts-${hz}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <Group justify="space-between" align="center" mb="xs">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>Classement par score et confiance • Horizon: {hz}</Text>
        </div>
        <Group gap="xs">
          <SegmentedControl
            value={hz}
            onChange={(v) => setHz(v as ForecastHorizon)}
            data={[
              { label: 'Court', value: 'short' },
              { label: 'Moyen', value: 'medium' },
              { label: 'Long',  value: 'long' },
            ]}
          />
          <Button variant="light" onClick={exportCsv}>Exporter CSV</Button>
          <Button onClick={() => refetch()} loading={isFetching}>Rafraîchir</Button>
        </Group>
      </Group>

      {isLoading && (
        <Alert title="Chargement" color="blue">Récupération des prévisions…</Alert>
      )}
      {error && (
        <Alert title="Erreur" color="red">Impossible de récupérer les prévisions ({String(error)})</Alert>
      )}
      {!isLoading && !error && items.length === 0 && (
        <Alert>Aucune prévision pour l’univers sélectionné.</Alert>
      )}

      <Grid gutter="md" mt="sm">
        {items.map((f) => {
          const dBadge = dirToBadge(f.direction);
          return (
            <Grid.Col key={`${f.symbol}-${f.horizon}`} span={{ base: 12, sm: 6, md: 4, lg: 3 }}>
              <Card withBorder shadow="sm">
                <Group justify="space-between" mb="xs">
                  <Group gap={8} wrap="nowrap">
                    <Title order={5} style={{ cursor: onSelectTicker ? 'pointer' : 'default' }}
                      onClick={() => onSelectTicker?.(f.symbol)}
                      title="Ouvrir la page du ticker"
                    >
                      {f.symbol}
                    </Title>
                    <BadgeDelta deltaType={dirToDelta(f.direction)} />
                    <Badge color={dBadge.color}>{dBadge.label}</Badge>
                  </Group>
                  <Badge variant="light">{f.horizon}</Badge>
                </Group>

                <Text c="dimmed" size="sm" lineClamp={1} mb="sm">
                  {/* optional name not present in ForecastItem; leave space for stocks meta enhancement */}
                </Text>

                <Group align="center" justify="space-between" mb="sm">
                  <RingProgress
                    size={80}
                    thickness={10}
                    sections={[
                      { value: f.score, color: f.score >= 66 ? 'green' : f.score >= 33 ? 'yellow' : 'red' },
                    ]}
                    label={
                      <Tooltip label={`Score ${f.score}/100`}>
                        <Text ta="center" fw={700} style={{ cursor: 'help' }}>
                          {f.score}
                        </Text>
                      </Tooltip>
                    }
                  />
                  <div style={{ lineHeight: 1.2 }}>
                    <Text size="sm" c="dimmed">Confiance</Text>
                    <Text fw={600}>{(f.confidence ?? 0)}%</Text>
                    <Text size="sm" c="dimmed" mt={8}>ER attendu</Text>
                    <Text fw={600}>{fmtPct(f.expectedReturn ?? 0)}</Text>
                  </div>
                </Group>

                <Group justify="space-between">
                  <ActionIcon
                    variant="light"
                    title="Voir détails de la prévision"
                    onClick={() => onOpenDetails?.(f.symbol)}
                  >
                    ⓘ
                  </ActionIcon>
                  <Group gap="xs">
                    <Button size="xs" variant="light" onClick={() => onSelectTicker?.(f.symbol)}>
                      Ouvrir
                    </Button>
                    <Button size="xs" onClick={() => onOpenDetails?.(f.symbol)}>
                      Détails
                    </Button>
                  </Group>
                </Group>

                {f.updatedAt && (
                  <Text c="dimmed" size="xs" mt="xs">
                    MAJ {new Date(f.updatedAt).toLocaleString()}
                  </Text>
                )}
              </Card>
            </Grid.Col>
          );
        })}
      </Grid>
    </Card>
  );
}
