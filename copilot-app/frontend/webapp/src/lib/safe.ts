/**
 * Safe access helpers - never-empty patterns implementation
 * These utilities help prevent JavaScript runtime errors like "Cannot read properties of undefined"
 */

/**
 * Ensure value is an array - return the array if it's already an array,
 * otherwise return an empty array. This is the safe pattern we recommend for all array access.
 */
export function ensureArray<T>(value: T[] | null | undefined): T[] {
  if (Array.isArray(value)) {
    return value;
  }
  return [];
}

/**
 * Safe null/not-null helper - returns the value if it's not null/undefined, otherwise returns fallback
 */
export function nn<T>(value: T | null | undefined, fallback: T): T {
  return value != null ? value : fallback;
}

/**
 * Check if array has items - safe way to check length without crashing on undefined
 */
export function hasItems<T>(value: T[] | null | undefined): boolean {
  return ensureArray(value).length > 0;
}

/**
 * Safe length function - returns length if array exists, otherwise returns 0
 */
export function safeLength<T>(value: T[] | null | undefined): number {
  return ensureArray(value).length;
}

/**
 * Safe map function - applies function if array exists, otherwise returns empty array
 */
export function safeMap<T, R>(array: T[] | null | undefined, fn: (item: T, index: number) => R): R[] {
  const arr = ensureArray(array);
  return arr.map(fn);
}

/**
 * Safe access to object properties with fallback
 */
export function safeGet(obj: any, path: string, fallback: any = null): any {
  try {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  } catch {
    return fallback;
  }
}

/**
 * Convert value to boolean safely
 */
export function safeBool(value: any, defaultValue: boolean = false): boolean {
  if (value === null || value === undefined) return defaultValue;
  return !!value;
}

/**
 * Convert value to string safely
 */
export function safeString(value: any, defaultValue: string = ''): string {
  if (value == null) return defaultValue;
  return String(value);
}

/**
 * Convert value to number safely
 */
export function safeNumber(value: any, defaultValue: number = 0): number {
  if (value == null) return defaultValue;
  const num = Number(value);
  return isNaN(num) ? defaultValue : num;
}

// Aliases for convenience
export const asNumber = safeNumber;
export const asString = safeString;
export const safeGetArray = ensureArray;
export const hasSafeArray = hasItems;