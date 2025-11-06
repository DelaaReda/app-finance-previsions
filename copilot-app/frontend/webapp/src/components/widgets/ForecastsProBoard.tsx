/**
 * Enhanced Forecasts Pro Board - Finance Copilot System
 * Advanced forecast visualization with ML/G4F hybrid insights
 */

import { useMemo, useState } from 'react';
import { Group, MultiSelect, SegmentedControl, Select, Alert, Table, Badge, Tooltip, Button, Card, Title, TextInput, Checkbox, Loader } from '@mantine/core';
import { AreaChart, BarList, DonutChart } from '@tremor/react';
import { IconRefresh, IconDownload, IconArrowUp, IconArrowDown, IconMinus, IconTrendingUp, IconTrendingDown, IconInfoCircle } from '@tabler/icons-react';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import { useForecasts } from '@/hooks/useForecasts';
import { ensureArray } from '@/lib/safe';

function exportCSV(items: any[]) {
  const cols = [
    'ticker',
    'name',
    'sector',
    'horizon',
    'score',
    'direction',
    'confidence',
    'expected_return_pct',
    'model_version',
    'forecasted_at',
    'themes',
    'explanation',
    'risk_factors',
    'hit_rate',
  ];
  const lines = [cols.join(',')];
  for (const it of items) {
    const row = cols
      .map((col) => {
        const value = col === 'themes' ? ensureArray(it[col]).join('|') : 
                     col === 'risk_factors' ? ensureArray(it[col]).join('|') : 
                     it[col];
        if (value == null) return '';
        const str = String(value);
        return str.includes(',') || str.includes('"') ? `"${str.replaceAll('"', '""')}"` : str;
      })
      .join(',');
    lines.push(row);
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(blob);
  anchor.download = 'forecasts-enhanced.csv';
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}

function formatSparkline(items: any[]) {
  return items
    .slice(0, 5)
    .filter((item) => item.ticker)
    .flatMap((item) =>
      ensureArray(item.sparkline).map((point: any) => ({
        date: point.date,
        [item.ticker]: point.value,
      })),
    )
    .reduce((acc: any[], row: Record<string, unknown>) => {
      if (!row.date) return acc;
      const existing = acc.find((entry) => entry.date === row.date);
      if (existing) Object.assign(existing, row);
      else acc.push(row);
      return acc;
    }, []);
}

function percent(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${value.toFixed(2)}%`;
}

export default function ForecastsProBoard() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [horizons, setHorizons] = useState<string[]>([]);
  const [themes, setThemes] = useState<string[]>([]);
  const [sort, setSort] = useState<string>('confidence_desc');
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [showExplanation, setShowExplanation] = useState<boolean>(true);
  const [selectedModelVersions, setSelectedModelVersions] = useState<string[]>([]); // For filtering by model version

  const { data, isLoading, isFetching, error, refetch } = useForecasts({
    tickers: tickers.length ? tickers : undefined,
    horizon: horizons.length ? horizons[0] : undefined, // Using first selected horizon for now
    themes: themes.length ? themes : undefined,
    limit: 200,
    sort_by: sort,
    min_confidence: minConfidence
  });

  const items = ensureArray(data?.rows || data?.items || []);

  const avgScore = useMemo(() => {
    const scores = items
      .map((item: any) => Number(item.final_score ?? item.score ?? 0))
      .filter((value: number) => Number.isFinite(value) && !isNaN(value));
    return scores.length ? scores.reduce((a: number, b: number) => a + b, 0) / scores.length : 0;
  }, [items]);

  const avgConfidence = useMemo(() => {
    const confidences = items
      .map((item: any) => Number(item.confidence ?? 0))
      .filter((value: number) => Number.isFinite(value) && !isNaN(value));
    return confidences.length ? confidences.reduce((a: number, b: number) => a + b, 0) / confidences.length : 0;
  }, [items]);

  const up = items.filter((item: any) => (item.direction || item.forecast_direction) === 'up').length;
  const down = items.filter((item: any) => (item.direction || item.forecast_direction) === 'down').length;
  const neutral = items.filter((item: any) => (item.direction || item.forecast_direction) === 'neutral').length;

  // Stats for donut chart
  const directionStats = [
    { name: 'Up', value: up, color: 'green' },
    { name: 'Down', value: down, color: 'red' },
    { name: 'Neutral', value: neutral, color: 'gray' },
  ];

  return (
    <Card data-testid="forecasts-pro" style={{ minHeight: '600px' }}>
      <Group justify="space-between" wrap="wrap">
        <div>
          <Group gap="xs" align="center">
            <Title order={4}>📈 Hybride Forecasts Pro</Title>
            <Tooltip label="Prévisions combinant ML + G4F pour des prédictions plus robustes et expliquées">
              <IconInfoCircle size={18} color="#4169E1" />
            </Tooltip>
          </Group>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginTop: '0.5rem', flexWrap: 'wrap' }}>
            <TextInput
              placeholder="Confidence min (0.0-1.0)"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value) || 0)}
              style={{ width: 140 }}
            />
            <Checkbox
              label="Afficher explications"
              checked={showExplanation}
              onChange={(e) => setShowExplanation(e.target.checked)}
            />
          </div>
        </div>
        
        <Group gap="xs" wrap="wrap">
          <MultiSelect
            placeholder="Tickers"
            searchable
            value={tickers}
            onChange={setTickers}
            data={[
              { value: 'SPY', label: 'SPY - S&P 500 ETF' },
              { value: 'QQQ', label: 'QQQ - Nasdaq 100 ETF' },
              { value: 'AAPL', label: 'AAPL - Apple Inc.' },
              { value: 'NVDA', label: 'NVDA - NVIDIA Corp.' },
              { value: 'MSFT', label: 'MSFT - Microsoft Corp.' },
              { value: 'GOOGL', label: 'GOOGL - Google/Alphabet' },
              { value: 'META', label: 'META - Meta Platforms' },
              { value: 'TSLA', label: 'TSLA - Tesla Inc.' },
              { value: 'AMZN', label: 'AMZN - Amazon.com' },
            ]}
            w={240}
          />
          
          <MultiSelect
            placeholder="Horizons"
            value={horizons}
            onChange={setHorizons}
            data={[
              { value: '1d', label: '1 jour' },
              { value: '5d', label: '5 jours' },
              { value: '1mo', label: '1 mois' },
              { value: '3mo', label: '3 mois' },
            ]}
            w={180}
          />
          
          <MultiSelect
            placeholder="Thèmes"
            value={themes}
            onChange={setThemes}
            data={['growth', 'value', 'momentum', 'dividend', 'quality', 'volatility', 'trend'].map((theme) => ({ value: theme, label: theme }))}
            w={180}
          />
          
          <Select
            value={sort}
            onChange={(value) => value && setSort(value)}
            w={200}
            data={[
              { value: 'confidence_desc', label: 'Confidence ↓' },
              { value: 'expected_return_desc', label: 'Retour attendu ↓' },
              { value: 'score_desc', label: 'Score ↓' },
              { value: 'ticker', label: 'Ticker ↑' },
            ]}
          />
          
          <Button 
            variant="light" 
            onClick={() => refetch()} 
            leftSection={<IconRefresh size={16} />} 
            loading={isFetching}
            title="Rafraîchir les prévisions"
          >
            Refresh
          </Button>
          
          <Button 
            variant="light" 
            onClick={() => exportCSV(items)} 
            leftSection={<IconDownload size={16} />}
            title="Exporter les prévisions en CSV"
          >
            Export CSV
          </Button>
          
          <FreshnessBadge freshness={data?.freshness ?? data?.last_update ?? undefined} />
        </Group>
      </Group>

      {isLoading && (
        <Alert color="blue" mt="md">
          <Group gap="xs">
            <Loader size="xs" />
            <span>Loading forecasts (ML + G4F)…</span>
          </Group>
        </Alert>
      )}
      
      {error && <Alert color="red" mt="md">Failed to load forecasts: {String(error)}</Alert>}

      {!isLoading && !error && items.length === 0 && (
        <Alert color="yellow" mt="md">
          <Group gap="xs">
            <IconInfoCircle size={16} />
            <span>Aucune prévision disponible. Le modèle hybride ML+G4F est en cours de calcul.</span>
          </Group>
        </Alert>
      )}

      {!isLoading && !error && items.length > 0 && (
        <>
          {/* Stats Summary */}
          <Group mt="md" gap="lg" wrap="wrap">
            <Badge size="lg" variant="filled" color="blue">
              Avg score: {avgScore.toFixed(2)}
            </Badge>
            <Badge size="lg" variant="filled" color="orange">
              Avg confidence: {(avgConfidence * 100).toFixed(1)}%
            </Badge>
            <Badge leftSection={<IconTrendingUp size={14} />} variant="light" color="green">
              {up} up
            </Badge>
            <Badge leftSection={<IconTrendingDown size={14} />} variant="light" color="red">
              {down} down
            </Badge>
            <Badge leftSection={<IconMinus size={14} />} variant="light" color="gray">
              {neutral} neutral
            </Badge>
          </Group>

          {/* Charts Section */}
          <Group mt="lg" grow align="stretch" wrap="nowrap">
            <div style={{ flex: 1 }}>
              <Title order={6}>Distribution des Directions</Title>
              <DonutChart
                data={directionStats}
                category="value"
                index="name"
                colors={['green', 'red', 'gray']}
                valueFormatter={(value) => `${value} prévisions`}
              />
            </div>
            
            <div style={{ flex: 2 }}>
              <Title order={6}>Top Prévisions</Title>
              <BarList
                data={items.slice(0, 10).map((item: any) => ({
                  name: `${item.ticker ?? item.symbol} (${item.horizon ?? 'N/A'})`,
                  value: Math.round(Number(item.confidence ?? item.final_score ?? 0) * 100),
                  href: `/ticker/${item.ticker ?? item.symbol}` // Navigate to ticker sheet
                }))}
                valueFormatter={(number) => `${number}%`}
              />
            </div>
          </Group>

          {/* Detailed Table */}
          <Table mt="lg" striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Ticker</Table.Th>
                <Table.Th>Horizon</Table.Th>
                <Table.Th>Score</Table.Th>
                <Table.Th>Direction</Table.Th>
                <Table.Th>Confidence</Table.Th>
                <Table.Th>Retour attendu</Table.Th>
                <Table.Th>Modèle</Table.Th>
                <Table.Th>Explication</Table.Th>
                <Table.Th>Risques</Table.Th>
                <Table.Th>Quand</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((item: any, index: number) => {
                const ticker = item.ticker ?? item.symbol;
                const direction = item.direction ?? item.forecast_direction;
                
                return (
                  <Table.Tr 
                    key={`${ticker}-${item.horizon ?? 'all'}-${index}`} 
                    style={{ backgroundColor: direction === 'up' ? '#e6f7e9' : direction === 'down' ? '#f9eaea' : '#f5f5f5' }}
                  >
                    <Table.Td>
                      <strong>{ticker}</strong>
                    </Table.Td>
                    <Table.Td>{item.horizon ?? 'N/A'}</Table.Td>
                    <Table.Td>{Number(item.final_score ?? item.score ?? 0).toFixed(2)}</Table.Td>
                    <Table.Td>
                      {direction === 'up' && <Badge color="green">UP</Badge>}
                      {direction === 'down' && <Badge color="red">DOWN</Badge>}
                      {direction === 'neutral' && <Badge color="gray">NEUTRAL</Badge>}
                      {direction !== 'up' && direction !== 'down' && direction !== 'neutral' && <Badge color="yellow">N/A</Badge>}
                    </Table.Td>
                    <Table.Td>{Math.round((item.confidence ?? 0) * 100)}%</Table.Td>
                    <Table.Td>{percent(item.expected_return_pct ?? item.expected_return)}</Table.Td>
                    <Table.Td>{item.model_version ?? 'hybrid_v1'}</Table.Td>
                    <Table.Td>
                      {showExplanation && item.explanation ? (
                        <Tooltip label={item.explanation}>
                          <span>{item.explanation.substring(0, 40)}{item.explanation.length > 40 ? '...' : ''}</span>
                        </Tooltip>
                      ) : '-'}
                    </Table.Td>
                    <Table.Td>
                      {item.risk_factors && Array.isArray(item.risk_factors) && item.risk_factors.length > 0 ? (
                        <Tooltip label={item.risk_factors.join(', ')}>
                          <Badge color="red">{item.risk_factors.length} risques</Badge>
                        </Tooltip>
                      ) : '-'}
                    </Table.Td>
                    <Table.Td>
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : 
                       item.forecasted_at ? new Date(item.forecasted_at).toLocaleString() : 
                       '—'}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </>
      )}
    </Card>
  );
}