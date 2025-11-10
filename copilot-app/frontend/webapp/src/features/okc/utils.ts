export type Trend = 'up' | 'down' | 'neutral';

/**
 * Merge Tailwind CSS classes with clsx and twMerge (improved version)
 * Handles conflicts and merges classes intelligently
 * Falls back to simple join if clsx/twMerge not available
 */
let clsx: any;
let twMerge: any;

try {
  clsx = require('clsx');
  twMerge = require('tailwind-merge');
} catch {
  // Fallback if packages not installed
  clsx = (...inputs: any[]) => inputs.filter(Boolean).join(' ');
  twMerge = (str: string) => str;
}

export function cn(...inputs: any[]) {
  try {
    return twMerge(clsx(inputs));
  } catch {
    // Ultimate fallback
    return inputs.filter(Boolean).join(' ');
  }
}

export function formatCurrency(amount: number, currency = 'USD', digits = 2): string {
  if (!Number.isFinite(amount)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(amount);
}

export function formatPercentage(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return '—';
  return `${value.toFixed(digits)}%`;
}

export function formatNumber(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function getTrendColor(value: number | Trend): string {
  if (typeof value === 'string') {
    if (value === 'up') return 'text-success';
    if (value === 'down') return 'text-danger';
    return 'text-muted';
  }
  if (value > 0) return 'text-success';
  if (value < 0) return 'text-danger';
  return 'text-muted';
}

export function getTrendIcon(value: number | Trend): string {
  if (typeof value === 'string') {
    if (value === 'up') return '↗';
    if (value === 'down') return '↘';
    return '→';
  }
  if (value > 0) return '↗';
  if (value < 0) return '↘';
  return '→';
}
