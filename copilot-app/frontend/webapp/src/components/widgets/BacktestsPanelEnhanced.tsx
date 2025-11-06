/**
 * Enhanced Backtests Panel with Tabs
 *
 * Comprehensive backtest analysis interface with:
 * - Overview (KPIs)
 * - Equity Curve visualization
 * - Monthly Returns breakdown
 * - Trades Explorer with filters and export
 *
 * Author: CLAUDE-CODE
 * Task: FC-PHASE2-001 - Backtests Trades Explorer
 */

import { useState, useMemo } from 'react';
import { Alert, Badge, Group, Tabs, Table, TextInput, Button, Stack, ActionIcon, Select } from '@mantine/core';
import { AreaChart, BarChart } from '@tremor/react';
import { Card, Title, Text } from '@/ui';
import { useBacktests } from '@/hooks/useBacktests';
import { IconDownload, IconFilter, IconX, IconSearch, IconFileTypeCsv, IconFileTypeZip } from '@tabler/icons-react';
import type { BacktestsResponse } from '@/types/backtests';

type Props = {
  strategy: string;
  universe?: string;
  benchmark?: string;
  horizon?: string;
};

/**
 * Export trades to CSV
 */
function exportToCSV(trades: NonNullable<BacktestsResponse['trades_sample']>, strategy: string) {
  const headers = ['Enter Date', 'Exit Date', 'Ticker', 'Return %'];
  const rows = trades.map(t => [
    t.enter,
    t.exit,
    t.ticker,
    (t.ret_pct ?? 0).toFixed(4)
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `backtests-trades-${strategy}-${new Date().toISOString().split('T')[0]}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Export trades to Parquet-like JSON (simplified)
 */
function exportToParquet(trades: NonNullable<BacktestsResponse['trades_sample']>, strategy: string) {
  const data = {
    schema: {
      enter: 'string',
      exit: 'string',
      ticker: 'string',
      ret_pct: 'float64'
    },
    data: trades
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `backtests-trades-${strategy}-${new Date().toISOString().split('T')[0]}.parquet.json`;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Trades Table Component with Filters
 */
function TradesTable({ trades, strategy }: { trades: NonNullable<BacktestsResponse['trades_sample']>; strategy: string }) {
  const [tickerFilter, setTickerFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [sortBy, setSortBy] = useState<'enter' | 'exit' | 'ret_pct'>('enter');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Get unique tickers for filter
  const uniqueTickers = useMemo(() => {
    const tickers = new Set(trades.map(t => t.ticker));
    return Array.from(tickers).sort();
  }, [trades]);

  // Filter and sort trades
  const filteredTrades = useMemo(() => {
    let result = [...trades];

    // Filter by ticker
    if (tickerFilter) {
      result = result.filter(t => t.ticker === tickerFilter);
    }

    // Filter by date
    if (dateFilter) {
      result = result.filter(t =>
        t.enter.includes(dateFilter) || t.exit.includes(dateFilter)
      );
    }

    // Sort
    result.sort((a, b) => {
      const aVal = sortBy === 'ret_pct' ? (a.ret_pct ?? 0) : a[sortBy];
      const bVal = sortBy === 'ret_pct' ? (b.ret_pct ?? 0) : b[sortBy];

      if (sortDirection === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });

    return result;
  }, [trades, tickerFilter, dateFilter, sortBy, sortDirection]);

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortDirection('desc');
    }
  };

  return (
    <Stack gap="md">
      {/* Filters */}
      <Group gap="md">
        <Select
          placeholder="Filter by ticker"
          data={[{ value: '', label: 'All Tickers' }, ...uniqueTickers.map(t => ({ value: t, label: t }))]}
          value={tickerFilter}
          onChange={(val) => setTickerFilter(val ?? '')}
          leftSection={<IconFilter size={16} />}
          clearable
          style={{ width: 200 }}
        />

        <TextInput
          placeholder="Filter by date (YYYY-MM-DD)"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          leftSection={<IconSearch size={16} />}
          rightSection={
            dateFilter && (
              <ActionIcon variant="subtle" onClick={() => setDateFilter('')}>
                <IconX size={14} />
              </ActionIcon>
            )
          }
          style={{ width: 250 }}
        />

        <Text size="sm" c="dimmed">
          {filteredTrades.length} / {trades.length} trades
        </Text>

        <div style={{ marginLeft: 'auto' }}>
          <Group gap="xs">
            <Button
              leftSection={<IconFileTypeCsv size={16} />}
              variant="light"
              size="sm"
              onClick={() => exportToCSV(filteredTrades, strategy)}
            >
              Export CSV
            </Button>
            <Button
              leftSection={<IconFileTypeZip size={16} />}
              variant="light"
              size="sm"
              onClick={() => exportToParquet(filteredTrades, strategy)}
            >
              Export Parquet
            </Button>
          </Group>
        </div>
      </Group>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th
                onClick={() => handleSort('enter')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Enter Date {sortBy === 'enter' && (sortDirection === 'asc' ? '↑' : '↓')}
              </Table.Th>
              <Table.Th
                onClick={() => handleSort('exit')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Exit Date {sortBy === 'exit' && (sortDirection === 'asc' ? '↑' : '↓')}
              </Table.Th>
              <Table.Th>Ticker</Table.Th>
              <Table.Th
                onClick={() => handleSort('ret_pct')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Return % {sortBy === 'ret_pct' && (sortDirection === 'asc' ? '↑' : '↓')}
              </Table.Th>
              <Table.Th>Days Held</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {filteredTrades.map((trade, idx) => {
              const enterDate = new Date(trade.enter);
              const exitDate = new Date(trade.exit);
              const daysHeld = Math.round((exitDate.getTime() - enterDate.getTime()) / (1000 * 60 * 60 * 24));
              const returnPct = trade.ret_pct ?? 0;
              const returnColor = returnPct > 0 ? 'green' : returnPct < 0 ? 'red' : 'gray';

              return (
                <Table.Tr key={idx}>
                  <Table.Td>{trade.enter}</Table.Td>
                  <Table.Td>{trade.exit}</Table.Td>
                  <Table.Td>
                    <Badge variant="light">{trade.ticker}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text c={returnColor} fw={500}>
                      {returnPct > 0 ? '+' : ''}{returnPct.toFixed(2)}%
                    </Text>
                  </Table.Td>
                  <Table.Td>{daysHeld}d</Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </div>

      {filteredTrades.length === 0 && (
        <Alert color="yellow">
          No trades match the current filters.
        </Alert>
      )}
    </Stack>
  );
}

/**
 * Enhanced Backtests Panel Component
 */
export default function BacktestsPanelEnhanced({ strategy, universe, benchmark, horizon }: Props) {
  const { data, isLoading, error } = useBacktests({ strategy, universe, benchmark, horizon });
  const [activeTab, setActiveTab] = useState<string>('overview');

  if (isLoading) {
    return (
      <Card data-testid="backtests-panel">
        <Alert color="blue">Loading backtest data...</Alert>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="backtests-panel">
        <Alert color="red">Failed to load backtests: {String(error)}</Alert>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card data-testid="backtests-panel">
        <Alert color="yellow">No backtest data available</Alert>
      </Card>
    );
  }

  return (
    <Card data-testid="backtests-panel">
      <Group justify="space-between" wrap="wrap" mb="md">
        <Title order={4}>📚 Backtests — {strategy}</Title>
        {data.updated_at && (
          <Text size="xs" c="dimmed">
            Updated: {new Date(data.updated_at).toLocaleString()}
          </Text>
        )}
      </Group>

      <Tabs value={activeTab} onChange={(val) => setActiveTab(val ?? 'overview')}>
        <Tabs.List>
          <Tabs.Tab value="overview">Overview</Tabs.Tab>
          <Tabs.Tab value="equity">Equity Curve</Tabs.Tab>
          <Tabs.Tab value="monthly">Monthly Returns</Tabs.Tab>
          <Tabs.Tab value="trades">
            Trades ({data.trades_sample?.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        {/* Overview Tab */}
        <Tabs.Panel value="overview" pt="md">
          <Stack gap="md">
            <Group gap="md" wrap="wrap">
              <Badge size="lg" variant="light" color="blue">
                CAGR {data.kpis.cagr_pct.toFixed(2)}%
              </Badge>
              <Badge size="lg" variant="light" color="green">
                Sharpe {data.kpis.sharpe.toFixed(2)}
              </Badge>
              <Badge size="lg" variant="light" color="teal">
                Sortino {data.kpis.sortino.toFixed(2)}
              </Badge>
              <Badge size="lg" variant="light" color="red">
                MaxDD {data.kpis.max_drawdown_pct.toFixed(1)}%
              </Badge>
              <Badge size="lg" variant="light" color="violet">
                WinRate {data.kpis.win_rate_pct.toFixed(1)}%
              </Badge>
              <Badge size="lg" variant="light" color="gray">
                Vol {data.kpis.volatility_pct.toFixed(1)}%
              </Badge>
              {data.kpis.avg_trade_pct !== undefined && (
                <Badge size="lg" variant="light" color="cyan">
                  Avg Trade {data.kpis.avg_trade_pct.toFixed(2)}%
                </Badge>
              )}
            </Group>

            <Alert color="blue" variant="light">
              <Text size="sm">
                <strong>Strategy:</strong> {strategy}
                {universe && <> | <strong>Universe:</strong> {universe}</>}
                {benchmark && <> | <strong>Benchmark:</strong> {benchmark}</>}
                {horizon && <> | <strong>Horizon:</strong> {horizon}</>}
              </Text>
            </Alert>
          </Stack>
        </Tabs.Panel>

        {/* Equity Curve Tab */}
        <Tabs.Panel value="equity" pt="md">
          <AreaChart
            data={data.equity_curve}
            index="date"
            categories={['strategy', ...(data.equity_curve.some((row) => row.benchmark != null) ? ['benchmark'] : [])]}
            colors={['blue', 'gray']}
            yAxisWidth={56}
            showLegend
            showAnimation
            curveType="linear"
          />
        </Tabs.Panel>

        {/* Monthly Returns Tab */}
        <Tabs.Panel value="monthly" pt="md">
          <BarChart
            data={(data.monthly_returns ?? []).map((row) => ({
              month: row.month,
              returns: row.pct ?? 0
            }))}
            index="month"
            categories={['returns']}
            colors={['emerald']}
            yAxisWidth={56}
            showLegend={false}
            showAnimation
          />
        </Tabs.Panel>

        {/* Trades Tab */}
        <Tabs.Panel value="trades" pt="md">
          {data.trades_sample && data.trades_sample.length > 0 ? (
            <TradesTable trades={data.trades_sample} strategy={strategy} />
          ) : (
            <Alert color="yellow">
              No trades data available for this backtest.
            </Alert>
          )}
        </Tabs.Panel>
      </Tabs>
    </Card>
  );
}
