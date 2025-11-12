/**
 * Utility functions for OKComputer Design components
 * Combines formatting, styling, and helper functions
 */
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind CSS classes with clsx and twMerge
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number as currency
 */
export function formatCurrency(amount: number, currency = 'USD', decimals = 2, locale: string = 'fr-CA'): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount);
}

/**
 * Format a number as percentage
 */
export function formatPercentage(value: number, decimals = 2, locale: string = 'fr-CA'): string {
  // Value is 0..100 (already scaled)
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/**
 * Format a number with specified decimals
 */
export function formatNumber(value: number, decimals = 2, locale: string = 'fr-CA'): string {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a number in compact notation (e.g., 1.2K, 3.4M)
 */
export function formatCompactNumber(value: number, locale: string = 'fr-CA'): string {
  return new Intl.NumberFormat(locale, {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);
}

/**
 * Format a date
 */
export function formatDate(date: Date | string, locale: string = 'fr-CA'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(d);
}

/**
 * Format a date with time
 */
export function formatDateTime(date: Date | string, locale: string = 'fr-CA'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

/**
 * Format a fraction (0..1) as percentage string in locale
 */
export function formatFractionToPercent(fraction: number, decimals = 2, locale: string = 'fr-CA'): string {
  const v = Math.max(-1, Math.min(1, fraction));
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(v);
}

/**
 * Get Tailwind color class for trend (positive/negative/neutral)
 */
export function getTrendColor(value: number): string {
  if (value > 0) return 'text-success';
  if (value < 0) return 'text-danger';
  return 'text-muted';
}

/**
 * Get trend icon (arrow) for value
 */
export function getTrendIcon(value: number): string {
  if (value > 0) return '↗';
  if (value < 0) return '↘';
  return '→';
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Generate a random ID
 */
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}

/**
 * Clamp a value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Linear interpolation
 */
export function lerp(start: number, end: number, factor: number): number {
  return start + (end - start) * factor;
}

/**
 * Smoothstep interpolation
 */
export function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
  return t * t * (3.0 - 2.0 * t);
}

/**
 * Check if value is a valid number
 */
export function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

/**
 * Safe division (returns fallback if denominator is 0)
 */
export function safeDivide(numerator: number, denominator: number, fallback = 0): number {
  return denominator !== 0 ? numerator / denominator : fallback;
}

/**
 * Calculate percentage change
 */
export function calculatePercentageChange(oldValue: number, newValue: number): number {
  return safeDivide(newValue - oldValue, oldValue) * 100;
}

/**
 * Calculate moving average
 */
export function calculateMovingAverage(data: number[], window: number): number[] {
  const result: number[] = [];
  for (let i = window - 1; i < data.length; i++) {
    const sum = data.slice(i - window + 1, i + 1).reduce((a, b) => a + b, 0);
    result.push(sum / window);
  }
  return result;
}

/**
 * Calculate standard deviation
 */
export function calculateStandardDeviation(data: number[]): number {
  const mean = data.reduce((a, b) => a + b, 0) / data.length;
  const squaredDiffs = data.map(value => Math.pow(value - mean, 2));
  const avgSquaredDiff = squaredDiffs.reduce((a, b) => a + b, 0) / data.length;
  return Math.sqrt(avgSquaredDiff);
}

/**
 * Calculate correlation coefficient
 */
export function calculateCorrelation(x: number[], y: number[]): number {
  const n = x.length;
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  return safeDivide(numerator, denominator);
}
