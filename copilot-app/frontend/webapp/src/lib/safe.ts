/**
 * Central place for safe guard helpers used across the UI
 */

export function safeArray<T>(value: T[] | null | undefined, fallback: T[] = []): T[] {
  return Array.isArray(value) ? value : fallback;
}

export function hasItems<T>(value: T[] | null | undefined): boolean {
  return safeArray(value).length > 0;
}

export function safeGet<T>(obj: any, path: string, defaultValue: T): T {
  if (!obj) return defaultValue;
  const keys = path.split('.');
  let current = obj;
  for (const key of keys) {
    current = current?.[key];
    if (current === undefined || current === null) {
      return defaultValue;
    }
  }
  return current as T;
}

export function safeNumber(value: number | null | undefined, defaultValue: number): number {
  if (typeof value === 'number' && !Number.isNaN(value)) {
    return value;
  }
  return defaultValue;
}

export function safeGetArray<T>(obj: any, path: string, defaultValue: T[] = []): T[] {
  if (!obj) return defaultValue;
  const value = safeGet<any>(obj, path, undefined as any);
  return safeArray(value, defaultValue);
}

export const hasSafeArray = (obj: any, path: string): boolean => hasItems(safeGetArray(obj, path));

export const safeMap = <T, R>(arr: T[] | null | undefined, mapFn: (item: T, index: number) => R): R[] =>
  safeArray(arr).map(mapFn);

export const safeLength = (arr: unknown[] | null | undefined): number => safeArray(arr).length;

export const isNonEmptyArray = <T>(arr: T[] | null | undefined): arr is T[] => hasItems(arr);

export function safeFormatNumber(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined) return 'N/A';
  return Number(value).toFixed(decimals);
}

export function getSafeRSIColor(rsi: number | null | undefined) {
  if (rsi === null || rsi === undefined) {
    return { color: '#cfd8dc' };
  }
  if (rsi > 70) return { color: '#f44336', fontWeight: 600 };
  if (rsi < 30) return { color: '#4caf50', fontWeight: 600 };
  return { color: '#ffb74d' };
}
