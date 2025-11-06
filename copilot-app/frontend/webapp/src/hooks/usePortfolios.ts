/**
 * usePortfolios - React Query hooks for Portfolio/Watchlist management
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-002 - Frontend integration for portfolios
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { qk } from '@/lib/keys'
import type { ApiResponse } from '@/types/api'

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
  const response = await fetch(`${API_BASE}/portfolios`)
  const data: ApiResponse<{ portfolios: Portfolio[]; count: number }> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to fetch portfolios')
  }
  
  return data.data.portfolios
}

async function fetchPortfolio(id: string): Promise<Portfolio> {
  const response = await fetch(`${API_BASE}/portfolios/${id}`)
  const data: ApiResponse<Portfolio> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to fetch portfolio')
  }
  
  return data.data
}

async function createPortfolio(request: PortfolioCreateRequest): Promise<Portfolio> {
  const response = await fetch(`${API_BASE}/portfolios`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const data: ApiResponse<Portfolio> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to create portfolio')
  }
  
  return data.data
}

async function updatePortfolio(id: string, request: PortfolioUpdateRequest): Promise<Portfolio> {
  const response = await fetch(`${API_BASE}/portfolios/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const data: ApiResponse<Portfolio> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to update portfolio')
  }
  
  return data.data
}

async function deletePortfolio(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/portfolios/${id}`, {
    method: 'DELETE',
  })
  const data: ApiResponse<{ deleted: boolean; id: string }> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to delete portfolio')
  }
}

async function addTickers(id: string, request: AddTickersRequest): Promise<Portfolio> {
  const response = await fetch(`${API_BASE}/portfolios/${id}/tickers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const data: ApiResponse<Portfolio> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to add tickers')
  }
  
  return data.data
}

async function removeTicker(id: string, ticker: string): Promise<Portfolio> {
  const response = await fetch(`${API_BASE}/portfolios/${id}/tickers/${ticker}`, {
    method: 'DELETE',
  })
  const data: ApiResponse<Portfolio> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to remove ticker')
  }
  
  return data.data
}

async function fetchPortfolioPerformance(id: string, benchmark?: string): Promise<PortfolioPerformance> {
  const params = new URLSearchParams()
  if (benchmark) params.set('benchmark', benchmark)
  
  const response = await fetch(`${API_BASE}/portfolios/${id}/performance?${params}`)
  const data: ApiResponse<PortfolioPerformance> = await response.json()
  
  if (!data.ok) {
    throw new Error(data.error || 'Failed to fetch performance')
  }
  
  return data.data
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
