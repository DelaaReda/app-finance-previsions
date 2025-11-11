/**
 * PerformanceCharts - Visualize portfolio performance with charts
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-004 - Performance Charts Frontend
 */
import { useState } from 'react'
import {
  Card,
  Title,
  Text,
  Group,
  Stack,
  Button,
  Loader,
  Alert,
  Badge,
  Grid,
  SimpleGrid,
  Select,
  SegmentedControl,
} from '@mantine/core'
import {
  IconAlertCircle,
  IconTrendingUp,
  IconTrendingDown,
  IconArrowUp,
  IconArrowDown,
} from '@tabler/icons-react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { usePortfolioTimeseries, type Portfolio } from '@/hooks/usePortfolios'
import { subMonths, subYears, startOfYear, format } from 'date-fns'

// ============================================================================
// Types
// ============================================================================

interface PerformanceChartsProps {
  portfolio: Portfolio
}

// ============================================================================
// Date Range Helpers
// ============================================================================

const DATE_RANGES = {
  '1M': () => subMonths(new Date(), 1),
  '3M': () => subMonths(new Date(), 3),
  'YTD': () => startOfYear(new Date()),
  '1Y': () => subYears(new Date(), 1),
  'All': () => subYears(new Date(), 10), // Max 10 years
}

const BENCHMARKS = [
  { value: 'SPY', label: 'SPY (S&P 500)' },
  { value: 'QQQ', label: 'QQQ (Nasdaq 100)' },
  { value: 'IWM', label: 'IWM (Russell 2000)' },
  { value: 'AGG', label: 'AGG (Bonds)' },
]

// ============================================================================
// Main Component
// ============================================================================

export function PerformanceCharts({ portfolio }: PerformanceChartsProps) {
  const [dateRange, setDateRange] = useState<string>('1Y')
  const [benchmark, setBenchmark] = useState<string>('SPY')

  // Calculate date range
  const startDate = DATE_RANGES[dateRange as keyof typeof DATE_RANGES]?.()
  const startDateStr = startDate ? format(startDate, 'yyyy-MM-dd') : undefined

  // Fetch performance data
  const { data, isLoading, error } = usePortfolioTimeseries(
    portfolio.id,
    benchmark,
    startDateStr
  )

  if (isLoading) {
    return (
      <Card p="lg">
        <Group justify="center" p="xl">
          <Loader size="lg" />
          <Text c="dimmed">Calculating performance...</Text>
        </Group>
      </Card>
    )
  }

  if (error) {
    return (
      <Card p="lg">
        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
          Failed to load performance data: {error.message}
        </Alert>
      </Card>
    )
  }

  if (!data || !data.portfolio || !data.metrics) {
    return (
      <Card p="lg">
        <Alert icon={<IconAlertCircle size={16} />} title="No Data" color="yellow">
          No performance data available for this period
        </Alert>
      </Card>
    )
  }

  // Prepare chart data (combine portfolio & benchmark)
  const chartData = data.portfolio.dates.map((date: string, index: number) => ({
    date,
    portfolio: data.portfolio.equity_curve[index],
    benchmark: data.benchmark?.equity_curve?.[index] || null,
    drawdown: data.portfolio.drawdown[index],
  }))

  const metrics = data.metrics
  const comparison = data.comparison

  return (
    <Stack gap="lg">
      {/* Controls */}
      <Card withBorder p="md">
        <Group justify="space-between">
          <SegmentedControl
            value={dateRange}
            onChange={setDateRange}
            data={[
              { label: '1M', value: '1M' },
              { label: '3M', value: '3M' },
              { label: 'YTD', value: 'YTD' },
              { label: '1Y', value: '1Y' },
              { label: 'All', value: 'All' },
            ]}
          />

          <Select
            value={benchmark}
            onChange={(value) => setBenchmark(value || 'SPY')}
            data={BENCHMARKS}
            label="Benchmark"
            style={{ width: 200 }}
          />
        </Group>
      </Card>

      {/* Equity Curve Chart */}
      <Card withBorder p="md">
        <Title order={4} mb="md">Equity Curve</Title>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(value) => format(new Date(value), 'MMM dd')}
            />
            <YAxis />
            <Tooltip
              labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
              formatter={(value: number) => `$${value.toFixed(2)}`}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="portfolio" 
              stroke="#2196F3" 
              strokeWidth={2}
              name="Portfolio"
              dot={false}
            />
            {chartData[0]?.benchmark !== null && (
              <Line 
                type="monotone" 
                dataKey="benchmark" 
                stroke="#9E9E9E" 
                strokeWidth={2}
                name={benchmark}
                dot={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Drawdown Chart */}
      <Card withBorder p="md">
        <Title order={4} mb="md">Drawdown</Title>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(value) => format(new Date(value), 'MMM dd')}
            />
            <YAxis />
            <Tooltip
              labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
              formatter={(value: number) => `${value.toFixed(2)}%`}
            />
            <Area 
              type="monotone" 
              dataKey="drawdown" 
              stroke="#f44336" 
              fill="#f44336"
              fillOpacity={0.3}
              name="Drawdown"
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Metrics Cards */}
      <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
        <MetricCard
          title="Total Return"
          value={metrics.total_return}
          format="percent"
          positive={metrics.total_return > 0}
        />
        <MetricCard
          title="Annualized Return"
          value={metrics.annualized_return}
          format="percent"
          positive={metrics.annualized_return > 0}
        />
        <MetricCard
          title="Volatility"
          value={metrics.volatility}
          format="percent"
        />
        <MetricCard
          title="Sharpe Ratio"
          value={metrics.sharpe_ratio}
          format="number"
          positive={metrics.sharpe_ratio > 1}
        />
        <MetricCard
          title="Max Drawdown"
          value={metrics.max_drawdown}
          format="percent"
          positive={metrics.max_drawdown > -0.1}
        />
        <MetricCard
          title="Win Rate"
          value={metrics.win_rate}
          format="percent"
          positive={metrics.win_rate > 0.5}
        />
        <MetricCard
          title="Best Day"
          value={metrics.best_day}
          format="percent"
          positive={true}
        />
        <MetricCard
          title="Worst Day"
          value={metrics.worst_day}
          format="percent"
          positive={false}
        />
      </SimpleGrid>

      {/* Benchmark Comparison */}
      {comparison && (
        <Card withBorder p="md">
          <Title order={4} mb="md">vs {comparison.benchmark_ticker}</Title>
          <Grid>
            <Grid.Col span={6}>
              <ComparisonRow
                label="Portfolio Return"
                value={comparison.portfolio_return}
                format="percent"
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <ComparisonRow
                label="Benchmark Return"
                value={comparison.benchmark_return}
                format="percent"
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <ComparisonRow
                label="Outperformance"
                value={comparison.outperformance}
                format="percent"
                highlight={true}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <ComparisonRow
                label="Correlation"
                value={comparison.correlation}
                format="number"
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <ComparisonRow
                label="Beta"
                value={comparison.beta}
                format="number"
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <ComparisonRow
                label="Alpha"
                value={comparison.alpha}
                format="percent"
                highlight={true}
              />
            </Grid.Col>
          </Grid>
        </Card>
      )}
    </Stack>
  )
}

// ============================================================================
// Helper Components
// ============================================================================

interface MetricCardProps {
  title: string
  value: number | null
  format: 'percent' | 'number'
  positive?: boolean
}

function MetricCard({ title, value, format, positive }: MetricCardProps) {
  if (value === null || value === undefined) {
    return (
      <Card withBorder p="md">
        <Text size="sm" c="dimmed">{title}</Text>
        <Text size="xl" fw={700} c="dimmed">—</Text>
      </Card>
    )
  }

  const formatted = format === 'percent' 
    ? `${(value * 100).toFixed(2)}%` 
    : value.toFixed(2)

  const color = positive !== undefined
    ? positive ? 'green' : 'red'
    : 'blue'

  const Icon = positive ? IconTrendingUp : IconTrendingDown

  return (
    <Card withBorder p="md">
      <Group justify="space-between" mb={4}>
        <Text size="sm" c="dimmed">{title}</Text>
        {positive !== undefined && <Icon size={16} color={color} />}
      </Group>
      <Text size="xl" fw={700} c={color}>{formatted}</Text>
    </Card>
  )
}

interface ComparisonRowProps {
  label: string
  value: number | null
  format: 'percent' | 'number'
  highlight?: boolean
}

function ComparisonRow({ label, value, format, highlight }: ComparisonRowProps) {
  if (value === null || value === undefined) {
    return (
      <Group justify="space-between">
        <Text size="sm">{label}</Text>
        <Text size="sm" c="dimmed">—</Text>
      </Group>
    )
  }

  const formatted = format === 'percent' 
    ? `${(value * 100).toFixed(2)}%` 
    : value.toFixed(2)

  const isPositive = value > 0
  const color = highlight && isPositive ? 'green' : highlight && !isPositive ? 'red' : undefined

  return (
    <Group justify="space-between">
      <Text size="sm">{label}</Text>
      {highlight ? (
        <Badge color={color} variant="light">
          {isPositive && '+'}{formatted}
        </Badge>
      ) : (
        <Text size="sm" fw={600}>{formatted}</Text>
      )}
    </Group>
  )
}
