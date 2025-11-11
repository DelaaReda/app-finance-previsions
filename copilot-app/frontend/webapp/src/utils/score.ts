/**
 * Utility functions for score normalization in the frontend
 */

/**
 * Converts a score to 0-100 range based on its original scale
 * - If |x| ≤ 1: maps from [-1,1] to [0,100] using ((x+1)/2)*100
 * - If 0 ≤ x ≤ 1: scales to [0,100] using x*100  
 * - Else: assumes already in [0,100] range or clamps to [0,100]
 * 
 * @param x The score to convert
 * @returns Number in 0-100 range or null if input is null/undefined
 */
export function toScore100(x?: number | null): number | null {
  if (x === undefined || x === null) {
    return null
  }
  
  // If value is in [-1, 1] range, normalize to [0, 100]
  if (Math.abs(x) <= 1) {
    // For values in [-1, 1], map to [0, 100]
    return Math.round(((x + 1) / 2) * 100)
  }
  
  // If value is in [0, 1] range, scale to [0, 100] 
  if (x >= 0 && x <= 1) {
    return Math.round(x * 100)
  }
  
  // Assume value is already in [0, 100] range, or clamp to [0, 100]
  return Math.min(Math.max(Math.round(x), 0), 100)
}

/**
 * Formats a score for display with "—"/"0/100" pattern
 * 
 * @param score The raw score value
 * @returns Formatted string for display (e.g., "42/100", "—", "0/100")
 */
export function formatScore(score?: number | null): string {
  const converted = toScore100(score)
  if (converted === null) {
    return '—'
  }
  return `${converted}/100`
}