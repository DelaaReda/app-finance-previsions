import React from 'react';

interface FreshnessBadgeProps {
  freshness?: string | null;
  stale?: boolean;
}

export function FreshnessBadge({ freshness, stale }: FreshnessBadgeProps) {
  if (!freshness) return null;
  
  const label = `Mise à jour: ${new Date(freshness).toLocaleString()}`;
  
  return (
    <span className={`badge ${stale ? "badge-warning" : "badge-ok"}`}>
      {label}{stale ? " • stale" : ""}
    </span>
  );
}