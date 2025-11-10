import { memo, useMemo } from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { cn } from '@/features/okc/utils';

type SparklinePoint = number | { value: number };

interface SparklineProps {
  data: SparklinePoint[];
  color?: string;
  height?: number;
  className?: string;
}

function normalizeData(data: SparklinePoint[]) {
  return data.map((d, i) => ({ i, v: typeof d === 'number' ? d : d?.value ?? 0 }));
}

export const Sparkline = memo(function Sparkline({ data, color = '#3b82f6', height = 36, className }: SparklineProps) {
  const rows = useMemo(() => normalizeData(data), [data]);

  if (!rows || rows.length === 0) {
    return <div className={cn('w-full', className)} style={{ height }} />;
  }

  return (
    <div className={cn('w-full', className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows} margin={{ top: 2, bottom: 0, left: 0, right: 0 }}>
          <defs>
            <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.4} />
              <stop offset="95%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill="url(#sparkFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
});

