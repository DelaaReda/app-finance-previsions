/**
 * Safety helpers to prevent UI crashes
 * Task: FC-UI-HELPERS-001
 * Author: CLAUDE-STABILITY-ARCHITECT-IRONMAN-42
 */

/**
 * Safely converts any value to an array
 * Prevents .map() crashes on undefined/null
 */
export function safeArray<T>(value: T[] | null | undefined): T[] {
  if (Array.isArray(value)) return value;
  return [];
}

/**
 * Checks if an array has items
 * Safe alternative to array?.length > 0
 */
export function hasItems<T>(value: T[] | null | undefined): boolean {
  return Array.isArray(value) && value.length > 0;
}

/**
 * Safe object access with fallback
 */
export function safeGet<T>(obj: any, path: string, defaultValue: T): T {
  try {
    const keys = path.split('.');
    let result = obj;
    for (const key of keys) {
      result = result?.[key];
      if (result === undefined || result === null) {
        return defaultValue;
      }
    }
    return result as T;
  } catch {
    return defaultValue;
  }
}
