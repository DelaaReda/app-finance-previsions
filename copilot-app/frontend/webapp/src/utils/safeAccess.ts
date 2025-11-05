/**
 * Utilities for safe array/object access in frontend components
 * Prevents "length/map of undefined" crashes
 */

/**
 * Safely access array property with fallback
 * @param obj The object that might contain the array property
 * @param prop The property name to access
 * @param fallback The fallback value if property is undefined or not an array
 * @returns The array if valid, otherwise the fallback value
 */
export function safeGetArray<T>(
  obj: any,
  prop: string,
  fallback: T[] = []
): T[] {
  if (!obj || typeof obj !== 'object') {
    return fallback;
  }
  
  const value = obj[prop];
  if (Array.isArray(value)) {
    return value;
  }
  
  return fallback;
}

/**
 * Safely check if an array property exists and has elements
 * @param obj The object that might contain the array property
 * @param prop The property name to check
 * @returns true if property exists and is a non-empty array
 */
export function hasSafeArray(obj: any, prop: string): boolean {
  if (!obj || typeof obj !== 'object') {
    return false;
  }
  
  const value = obj[prop];
  return Array.isArray(value) && value.length > 0;
}

/**
 * Safe map function that checks if array exists before mapping
 * @param array The array to map over
 * @param callback The mapping function
 * @param fallback Fallback value if array is not valid
 * @returns Mapped array or fallback
 */
export function safeMap<T, U>(
  array: any,
  callback: (item: T, index: number) => U,
  fallback: U[] = []
): U[] {
  if (Array.isArray(array)) {
    return array.map(callback);
  }
  
  return fallback;
}

/**
 * Safe length check that returns 0 for undefined/non-array values
 * @param array The array to check length of
 * @returns Length of array or 0 if not valid array
 */
export function safeLength(array: any): number {
  if (Array.isArray(array)) {
    return array.length;
  }
  
  return 0;
}