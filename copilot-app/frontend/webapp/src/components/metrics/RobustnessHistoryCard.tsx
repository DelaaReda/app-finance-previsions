import { AreaChart, Card, Text, Title } from '@/ui';
import { ensureArray } from '@/lib/safe';
import { robustScore } from '@/lib/robustScore';

type Snapshot = {
  date: string;
  stats?: {
    cagr?: number;
    maxDrawdown?: number;
    maxDD?: number;
    winRate?: number;
    trades?: number;
  };
};

export default function RobustnessHistoryCard({ snapshots }: { snapshots?: Snapshot[] }) {
  const dataset = ensureArray(snapshots).map((snapshot) => {
    const stats = snapshot?.stats ?? {};
    const result = robustScore({
      cagr: stats.cagr,
      maxDD: Math.abs(stats.maxDrawdown ?? stats.maxDD ?? 0),
      winRate: stats.winRate,
      trades: stats.trades,
    });

    return {
      date: snapshot?.date ?? '',
      score: result.total,
    };
  });

  return (
    <Card withBorder data-testid="card-robustness-history">
      <Title order={4}>Historique de robustesse</Title>
      <Text c="dimmed" size="sm" mt={4}>
        Évolution du score (0-100). Objectif: stabilité dans le temps.
      </Text>
      {dataset.length === 0 ? (
        <Text c="dimmed" size="sm" mt={12}>
          Aucun historique disponible pour l’instant.
        </Text>
      ) : (
        <AreaChart
          className="h-64"
          data={dataset}
          index="date"
          categories={['score']}
          minValue={0}
          maxValue={100}
          valueFormatter={(value) => `${value}`}
          showLegend={false}
          curveType="monotone"
          yAxisWidth={48}
        />
      )}
    </Card>
  );
}
