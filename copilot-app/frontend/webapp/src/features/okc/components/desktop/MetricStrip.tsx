import { cn } from '@/features/okc/utils';

export type MetricTone = 'low' | 'moderate' | 'high' | 'neutral';

export interface StripMetric {
  label: string;
  value: number | string;
  tone?: MetricTone;
}

function toneColor(tone?: MetricTone) {
  switch (tone) {
    case 'low':
      return 'text-emerald-500';
    case 'moderate':
      return 'text-amber-500';
    case 'high':
      return 'text-red-500';
    default:
      return 'text-text';
  }
}

export function MetricStrip({ items, className }: { items: StripMetric[]; className?: string }) {
  return (
    <div className={cn('grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 text-center bg-surface-elevated/40 border border-border p-3 rounded-lg', className)}>
      {items.map((m, idx) => (
        <div key={`${m.label}-${idx}`} className="min-w-0">
          <div className="text-xs text-muted mb-1 truncate">{m.label}</div>
          <div className={cn('font-semibold', toneColor(m.tone))} style={{ fontVariantNumeric: 'tabular-nums' }}>
            {typeof m.value === 'number' ? m.value.toFixed(2) : m.value}
          </div>
        </div>
      ))}
    </div>
  );
}

