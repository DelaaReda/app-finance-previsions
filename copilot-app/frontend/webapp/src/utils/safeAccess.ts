/**
 * Safe access utilities to prevent "reading property of undefined" errors
 */

export const safeGet = <T = any>(obj: any, path: string, defaultValue?: T): T | undefined => {
  try {
    const keys = path.split('.');
    let current = obj;
    
    for (const key of keys) {
      if (current === null || current === undefined) {
        return defaultValue;
      }
      current = current[key];
    }
    
    return current !== undefined ? current : defaultValue;
  } catch (e) {
    return defaultValue;
  }
};

export const safeArray = <T>(arr: T[] | null | undefined, defaultValue: T[] = []): T[] => {
  if (Array.isArray(arr)) {
    return arr;
  }
  return defaultValue;
};

export const safeString = (str: string | null | undefined, defaultValue: string = ''): string => {
  if (typeof str === 'string') {
    return str;
  }
  return defaultValue;
};

export const safeNumber = (num: number | null | undefined, defaultValue: number = 0): number => {
  if (typeof num === 'number' && !isNaN(num)) {
    return num;
  }
  return defaultValue;
};

/**
 * Safe mapper that handles undefined arrays
 */
export const safeMap = <T, R>(
  arr: T[] | null | undefined,
  callback: (item: T, index: number) => R,
  defaultValue: R[] = []
): R[] => {
  if (Array.isArray(arr)) {
    return arr.map(callback);
  }
  return defaultValue;
};

/**
 * Safe length checker for arrays
 */
export const safeLength = (arr: any): number => {
  if (Array.isArray(arr)) {
    return arr.length;
  }
  return 0;
};

/**
 * Guard for checking if an array is defined and not empty
 */
export const isNonEmptyArray = <T>(arr: T[] | null | undefined): arr is T[] => {
  return Array.isArray(arr) && arr.length > 0;
};

/**
 * Safe array getter that uses dot notation for nested properties
 */
export const safeGetArray = <T>(obj: any, path: string, defaultValue: T[] = []): T[] => {
  try {
    const keys = path.split('.');
    let current = obj;
    
    for (const key of keys) {
      if (current === null || current === undefined) {
        return defaultValue;
      }
      current = current[key];
    }
    
    return Array.isArray(current) ? current : defaultValue;
  } catch (e) {
    return defaultValue;
  }
};
// Backwards-compatible aliases used across the codebase
export function safeGetArrayAlias<T>(obj: any, prop: string, fallback: T[] = []): T[] {
  const value = safeGet<any>(obj, prop, undefined as any);
  return Array.isArray(value) ? (value as T[]) : fallback;
}

export function hasSafeArray(obj: any, prop: string): boolean {
  const value = safeGet<any>(obj, prop, undefined as any);
  return Array.isArray(value) && value.length > 0;
}

// Provide a commonly named alias 'safeGetArray' for compatibility
// note: `safeGetArray` is the canonical function above; keep `safeGetArrayAlias` for legacy imports