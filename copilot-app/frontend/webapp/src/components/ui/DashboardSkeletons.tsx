/**
 * Dashboard Skeletons - Composants skeleton cohérents pour le dashboard
 * Améliore l'expérience de chargement avec des skeletons aux bonnes dimensions
 */

import { Skeleton } from '@mantine/core';

export function ForecastCardsSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <Skeleton height={20} width={60} />
            <Skeleton height={18} width={40} />
          </div>
          <div className="flex items-center gap-3 mb-3">
            <Skeleton height={52} width={52} radius="xl" />
            <div className="flex-1">
              <Skeleton height={16} width="60%" mb={8} />
              <Skeleton height={14} width="80%" />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <Skeleton height={24} width={80} radius="md" />
            <Skeleton height={28} width={60} radius="md" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function TopStocksSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center justify-between py-3 px-4 bg-zinc-900/30 rounded-lg">
          <div className="flex items-center gap-3">
            <Skeleton height={16} width={50} />
            <Skeleton height={14} width={120} />
          </div>
          <div className="flex items-center gap-4">
            <Skeleton height={16} width={60} />
            <Skeleton height={20} width={70} radius="md" />
            <Skeleton height={14} width={80} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function NewsFeedSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex gap-3 p-3 bg-zinc-900/30 rounded-lg">
          <div className="flex-1">
            <Skeleton height={16} width="90%" mb={8} />
            <Skeleton height={12} width="40%" mb={4} />
            <Skeleton height={12} width="30%" />
          </div>
          <Skeleton height={16} width={40} />
        </div>
      ))}
    </div>
  );
}

export function MacroIndicatorsSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <Skeleton height={12} width={60} />
            <Skeleton height={16} width={40} radius="md" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton height={20} width={50} />
            <Skeleton height={14} width={14} radius="xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function KPIBarSkeleton() {
  return (
    <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
      <div className="flex items-center justify-between gap-6">
        <div className="flex items-center gap-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton height={16} width={16} radius="sm" />
              <div>
                <Skeleton height={12} width={80} mb={4} />
                <Skeleton height={18} width={40} />
              </div>
            </div>
          ))}
        </div>
        <Skeleton height={32} width={100} radius="md" />
      </div>
    </div>
  );
}