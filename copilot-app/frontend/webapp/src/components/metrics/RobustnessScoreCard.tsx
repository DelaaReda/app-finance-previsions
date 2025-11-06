import { Badge, Card, RingProgress, Text, Title } from '@/ui';
import type { BacktestSummary } from '@/lib/robustScore';
import { robustScore } from '@/lib/robustScore';

function scoreColor(total: number) {
  if (total >= 90) return 'teal';
  if (total >= 80) return 'green';
  if (total >= 70) return 'indigo';
  if (total >= 60) return 'yellow';
  return 'red';
}

export default function RobustnessScoreCard({
  summary,
  title = 'Score de robustesse',
}: {
  summary?: BacktestSummary;
  title?: string;
}) {
  const result = robustScore(summary);
  const color = scoreColor(result.total);

  return (
    <Card withBorder data-testid="card-robustness">
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, justifyContent: 'space-between' }}>
        <div style={{ display: 'grid', gap: 6 }}>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" size="sm">
            Synthèse pondérée: performance, risque, régularité, taille d’échantillon.
          </Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
            <Badge color="blue" variant="light">
              CAGR {result.parts.CAGR}
            </Badge>
            <Badge color="grape" variant="light">
              DD {result.parts.Drawdown}
            </Badge>
            <Badge color="cyan" variant="light">
              Win {result.parts.WinRate}
            </Badge>
            <Badge color="gray" variant="light">
              Trades {result.parts.Trades}
            </Badge>
          </div>
        </div>
        <div style={{ display: 'grid', placeItems: 'center' }}>
          <RingProgress
            data-testid="ring-robustness"
            label={
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{result.total}</div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>{result.grade}</div>
              </div>
            }
            sections={[{ value: result.total, color }]}
          />
        </div>
      </div>
    </Card>
  );
}
