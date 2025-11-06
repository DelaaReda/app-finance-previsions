// Transitional shim for older imports that referenced '@/utils/safeAccess'
// Re-exports the canonical helpers from '@/lib/safe' to avoid touching many files at once.
import {
  safeGet as _safeGet,
  safeGetArray as _safeGetArray,
  hasSafeArray as _hasSafeArray,
  safeMap as _safeMap,
  safeLength as _safeLength,
  safeNumber as _safeNumber,
} from '@/lib/safe';

export const safeGet = _safeGet;
export const safeGetArray = _safeGetArray;
export const hasSafeArray = _hasSafeArray;
export const safeMap = _safeMap;
export const safeLength = _safeLength;
export const safeNumber = _safeNumber;

// Additional convenience helpers kept to minimize churn
export const safeGetArrayAlias = _safeGetArray;

export default {
  safeGet,
  safeGetArray,
  hasSafeArray,
  safeMap,
  safeLength,
  safeNumber,
};
/**
 * Safely access any property with fallback (using dot notation)
 * @param obj The object to access
 * @param path The property path (e.g. 'data.user.name' or 'rows.0.symbol')
 * @param defaultValue Default value if property not found
 * @returns Property value or defaultValue
 */
export function safeGet<T>(obj: any, path: string, defaultValue: T): T {
  if (obj === null || obj === undefined) {
    return defaultValue;
  }
  
  const keys = path.split('.');
  let current = obj;
  
  for (const key of keys) {
    if (current === null || current === undefined) {
      return defaultValue;
    }
    current = current[key];
  }
  
  return current !== undefined ? current : defaultValue;
}

/**
 * Safely access array property with fallback using dot notation
 * @param obj The object that might contain the array property
 * @param path The property path (e.g. 'data.rows' or 'items')
 * @param defaultValue Default value if property not found or not an array
 * @returns Array if valid, otherwise defaultValue
 */
export function safeGetArray<T>(obj: any, path: string, defaultValue: T[] = []): T[] {
  if (obj === null || obj === undefined) {
    return defaultValue;
  }
  
  const keys = path.split('.');
  let current = obj;
  
  for (const key of keys) {
    if (current === null || current === undefined) {
      return defaultValue;
    }
    current = current[key];
  }
  
  return Array.isArray(current) ? current : defaultValue;
}

/**
 * Safe guard for non-empty arrays
 */
export const hasSafeArray = (obj: any, prop: string): boolean => {
  const value = safeGet<any>(obj, prop, undefined);
  return Array.isArray(value) && value.length > 0;
};

/**
 * Safe map function that checks array validity before mapping
 */
export const safeMap = <T, U>(array: T[], callback: (item: T, index: number) => U, defaultValue: U[] = []): U[] => {
  if (!Array.isArray(array)) {
    return defaultValue;
  }
  return array.map(callback);
};

/**
 * Safe length check that works with arrays and fallbacks
 */
export const safeLength = (array: any): number => {
  if (Array.isArray(array)) {
    return array.length;
  }
  return 0;
};

/**
 * Guard for checking if an array is defined and not empty
 */
export const isNonEmptyArray = <T>(arr: T[] | null | undefined): arr is T[] => {
  return Array.isArray(arr) && arr.length > 0;
}

/**
 * Format a number for display, showing "N/A" if null or undefined
 * @param value The value to format
 * @param decimals Number of decimal places (default 2)
 * @returns Formatted string with number of "N/A" if null
 */
export function safeFormatNumber(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  
  return value.toFixed(decimals);
}

/**
 * Get a safe color for RSI values with handling for null values
 * @param rsi The RSI value
 * @returns Color style object
 */
export function getSafeRSIColor(rsi: number | null | undefined) {
  if (rsi === null || rsi === undefined) {
    return { color: '#cfd8dc' }; // neutral gray
  }
  
  if (rsi > 70) return { color: '#f44336', fontWeight: 600 }; // oversold (red)
  if (rsi < 30) return { color: '#4caf50', fontWeight: 600 }; // oversold (green) 
  return { color: '#ffb74d' }; // neutral (orange)
}