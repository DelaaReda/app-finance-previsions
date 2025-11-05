import { apiGet, apiPost } from './client';
import type { ApiResponse } from '../types/common';
import { safeArray, safeGet, safeNumber } from '@/lib/safe';

/**
 * Safe API client that handles undefined responses and provides safe access patterns
 */
export const safeApiGet = async <T>(path: string, params?: Record<string, any>): Promise<ApiResponse<T>> => {
  try {
    const response = await apiGet<T>(path, params);
    
    // If the response is successful but data is undefined or null, return safe defaults
    if (response.ok && (response.data === undefined || response.data === null)) {
      // For arrays, return empty array; for objects, return empty object
      return {
        ok: true,
        data: [] as any
      };
    }
    
    return response;
  } catch (error) {
    // In case of error, return a safe response with empty data
    console.error(`Safe API GET error for ${path}:`, error);
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      data: undefined as any
    };
  }
};

export const safeApiPost = async <T>(path: string, data?: any): Promise<ApiResponse<T>> => {
  try {
    const response = await apiPost<T>(path, data);
    
    // If the response is successful but data is undefined or null, return safe defaults
    if (response.ok && (response.data === undefined || response.data === null)) {
      return {
        ok: true,
        data: [] as any
      };
    }
    
    return response;
  } catch (error) {
    // In case of error, return a safe response with empty data
    console.error(`Safe API POST error for ${path}:`, error);
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      data: undefined as any
    };
  }
};

/**
 * Convenience functions for common data patterns
 */

// For fetching data that should be an array
export const fetchSafeArray = async <T>(
  path: string, 
  params?: Record<string, any>,
  defaultValue: T[] = []
): Promise<T[]> => {
  try {
    const response = await safeApiGet<T[]>(path, params);
    if (response.ok) {
      return safeArray(response.data, defaultValue);
    }
  } catch (error) {
    console.error(`Error fetching array from ${path}:`, error);
  }
  return defaultValue;
};

// For fetching paginated data
export interface PaginatedResponse<T> {
  rows: T[];
  count: number;
}

export const fetchSafePaginated = async <T>(
  path: string,
  params?: Record<string, any>
): Promise<PaginatedResponse<T>> => {
  try {
    const response = await safeApiGet<PaginatedResponse<T>>(path, params);
    if (response.ok) {
      // Ensure rows is always an array
      const rows = safeArray(
        response.data && typeof response.data === 'object' ? response.data.rows : undefined,
        []
      ) as T[];
  // Ensure count is always a number (never undefined)
  const count = safeNumber(safeGet<number>(response.data, 'count', undefined), 0);
      
      return { rows, count };
    }
  } catch (error) {
    console.error(`Error fetching paginated data from ${path}:`, error);
  }
  return { rows: [], count: 0 };
};

// For fetching single objects
export const fetchSafeObject = async <T>(
  path: string,
  params?: Record<string, any>,
  defaultValue: T = {} as T
): Promise<T> => {
  try {
    const response = await safeApiGet<T>(path, params);
    if (response.ok && response.data) {
      return response.data;
    }
  } catch (error) {
    console.error(`Error fetching object from ${path}:`, error);
  }
  return defaultValue;
};