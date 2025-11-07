/**
 * usePortfolios - React Query hooks for Portfolio/Watchlist management
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-002 - Frontend integration for portfolios
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { qk } from '@/lib/keys'
import { api } from '@/api/client'

// ============================================================================
// Types
// ============================================================================

export interface Portfolio {
  id: string
  name: string
  description: string
  tickers: string[]
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export interface PortfolioPerformance {
  portfolio_id: string
  portfolio_name: string
  tickers_count: number
  total_return: number | null
  avg_return: number | null
  volatility: number | null
  sharpe_ratio: number | null
  vs_benchmark: {
    benchmark: string
    outperformance: number | null
  } | null
  calculated_at: string
}

export interface PortfolioCreateRequest {
  name: string
  description?: string
  tickers?: string[]
  metadata?: Record<string, any>
}

export interface PortfolioUpdateRequest {
  name?: string
  description?: string
  tickers?: string[]
  metadata?: Record<string, any>
}

export interface AddTickersRequest {
  tickers: string[]
}

// ============================================================================
// API Functions
// ============================================================================

const API_BASE = '/api'

async function fetchPortfolios(): Promise<Portfolio[]> {
  const data = await api.fetchJson<{ portfolios: Portfolio[]; count: number }>(`${API_BASE}/portfolios`)
  return data.portfolios
}

async function fetchPortfolio(id: string): Promise<Portfolio> {
  return api.fetchJson<Portfolio>(`${API_BASE}/portfolios/${id}`)
}

async function createPortfolio(request: PortfolioCreateRequest): Promise<Portfolio> {
  return api.fetchJson<Portfolio>(`${API_BASE}/portfolios`, {
    method: 'POST',
    body: request,
  })
}

async function updatePortfolio(id: string, request: PortfolioUpdateRequest): Promise<Portfolio> {
  return api.fetchJson<Portfolio>(`${API_BASE}/portfolios/${id}`, {
    method: 'PUT',
    body: request,
  })
}

async function deletePortfolio(id: string): Promise<void> {
  await api.fetchJson(`${API_BASE}/portfolios/${id}`, {
    method: 'DELETE',
  })
}

async function addTickers(id: string, request: AddTickersRequest): Promise<Portfolio> {
  return api.fetchJson<Portfolio>(`${API_BASE}/portfolios/${id}/tickers`, {
    method: 'POST',
    body: request,
  })
}

async function removeTicker(id: string, ticker: string): Promise<Portfolio> {
  return api.fetchJson<Portfolio>(`${API_BASE}/portfolios/${id}/tickers/${ticker}`, {
    method: 'DELETE',
  })
}

async function fetchPortfolioPerformance(id: string, benchmark?: string): Promise<PortfolioPerformance> {
  return api.fetchJson<PortfolioPerformance>(`${API_BASE}/portfolios/${id}/performance`, {
    searchParams: benchmark ? { benchmark } : undefined,
  })
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * List all portfolios
 */
export function usePortfolios() {
  return useQuery({
    queryKey: qk.portfolios(),
    queryFn: fetchPortfolios,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  })
}

/**
 * Get single portfolio by ID
 */
export function usePortfolio(id: string | null) {
  return useQuery({
    queryKey: qk.portfolio(id ?? ''),
    queryFn: () => fetchPortfolio(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })
}

/**
 * Get portfolio performance metrics
 */
export function usePortfolioPerformance(id: string | null, benchmark?: string) {
  return useQuery({
    queryKey: qk.portfolioPerformance(id ?? '', benchmark),
    queryFn: () => fetchPortfolioPerformance(id!, benchmark),
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // 10 minutes (performance is expensive)
    retry: 2,
  })
}

/**
 * Create portfolio mutation
 */
export function useCreatePortfolio() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: createPortfolio,
    onSuccess: () => {
      // Invalidate portfolios list
      queryClient.invalidateQueries({ queryKey: qk.portfolios() })
    },
  })
}

/**
 * Update portfolio mutation
 */
export function useUpdatePortfolio() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PortfolioUpdateRequest }) =>
      updatePortfolio(id, data),
    onSuccess: (updatedPortfolio) => {
      // Invalidate both list and single portfolio
      queryClient.invalidateQueries({ queryKey: qk.portfolios() })
      queryClient.invalidateQueries({ queryKey: qk.portfolio(updatedPortfolio.id) })
    },
  })
}

/**
 * Delete portfolio mutation
 */
export function useDeletePortfolio() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: deletePortfolio,
    onSuccess: (_, deletedId) => {
      // Invalidate list and remove from cache
      queryClient.invalidateQueries({ queryKey: qk.portfolios() })
      queryClient.removeQueries({ queryKey: qk.portfolio(deletedId) })
    },
  })
}

/**
 * Add tickers to portfolio mutation
 */
export function useAddTickers() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, tickers }: { id: string; tickers: string[] }) =>
      addTickers(id, { tickers }),
    onSuccess: (updatedPortfolio) => {
      // Invalidate both list and single portfolio
      queryClient.invalidateQueries({ queryKey: qk.portfolios() })
      queryClient.invalidateQueries({ queryKey: qk.portfolio(updatedPortfolio.id) })
    },
  })
}

/**
 * Remove ticker from portfolio mutation
 */
export function useRemoveTicker() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, ticker }: { id: string; ticker: string }) =>
      removeTicker(id, ticker),
    onSuccess: (updatedPortfolio) => {
      // Invalidate both list and single portfolio
      queryClient.invalidateQueries({ queryKey: qk.portfolios() })
      queryClient.invalidateQueries({ queryKey: qk.portfolio(updatedPortfolio.id) })
    },
  })
}

/**
 * Get portfolio performance time series for charts
 */
export function usePortfolioTimeseries(
  id: string | null,
  benchmark: string = 'SPY',
  startDate?: string,
  endDate?: string
) {
  return useQuery({
    queryKey: qk.portfolioPerformance(id ?? '', benchmark),
    queryFn: async () => {
      if (!id) return null
      
      const params = new URLSearchParams()
      params.set('benchmark', benchmark)
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      
      const response = await fetch(`${API_BASE}/portfolios/${id}/performance/timeseries?${params}`)
      const data: ApiResponse<any> = await response.json()
      
      if (!data.ok) {
        throw new Error(data.error || 'Failed to fetch performance timeseries')
      }
      
      return data.data
    },
    enabled: !!id,
    staleTime: 60 * 60 * 1000, // 1 hour (performance data is expensive)
    retry: 2,
  })
}
