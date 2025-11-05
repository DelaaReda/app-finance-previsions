import { Chip } from '@mui/material';

interface FreshnessBadgeProps {
  stale?: boolean;
  freshness?: string;
}

export default function FreshnessBadge({ stale, freshness }: FreshnessBadgeProps) {
  if (!freshness) return null;
  
  const label = stale ? `Stale: ${new Date(freshness).toLocaleString()}` : `Fresh: ${new Date(freshness).toLocaleString()}`;
  const color = stale ? 'warning' : 'success';
  
  return <Chip size="small" label={label} color={color as any} />;
}