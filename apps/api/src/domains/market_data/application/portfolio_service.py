"""
Portfolio Service - Manage user portfolios/watchlists
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-PORTFOLIO-001 - Portfolio/Watchlist management
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

try:
    from services import portfolio_performance_service as _performance_module
except Exception:  # pragma: no cover
    try:
        from domains.market_data.application import portfolio_performance_service as _performance_module
    except Exception:  # pragma: no cover
        _performance_module = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_performance_service():
    if _performance_module is None:
        raise ImportError("portfolio_performance_service is unavailable")
    return _performance_module.get_performance_service()


def _equal_weights(tickers: List[str]) -> Dict[str, float]:
    if not tickers:
        return {}
    weight = round(1.0 / len(tickers), 4)
    return {ticker: weight for ticker in sorted(tickers)}


def _resolve_portfolio_weights(
    tickers: List[str],
    metadata: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, float], str, List[str]]:
    normalized_tickers = sorted(str(ticker or "").strip().upper() for ticker in tickers if str(ticker or "").strip())
    if not normalized_tickers:
        return {}, "empty_portfolio", []

    fallback_weights = _equal_weights(normalized_tickers)
    metadata_dict = metadata if isinstance(metadata, dict) else {}
    raw_weights = metadata_dict.get("weights")
    if raw_weights is None:
        raw_weights = metadata_dict.get("position_weights")
    if not isinstance(raw_weights, dict) or not raw_weights:
        return fallback_weights, "equal_weight", []

    warnings: List[str] = []
    filtered_weights: Dict[str, float] = {}
    invalid_tickers: List[str] = []
    unknown_tickers: List[str] = []

    for raw_ticker, raw_weight in raw_weights.items():
        ticker = str(raw_ticker or "").strip().upper()
        if not ticker:
            continue
        if ticker not in normalized_tickers:
            unknown_tickers.append(ticker)
            continue
        try:
            parsed_weight = float(raw_weight)
        except (TypeError, ValueError):
            invalid_tickers.append(ticker)
            continue
        if parsed_weight <= 0:
            invalid_tickers.append(ticker)
            continue
        filtered_weights[ticker] = parsed_weight

    if invalid_tickers:
        warnings.append(
            f"Ignored invalid saved weights for {', '.join(sorted(set(invalid_tickers)))}."
        )
    if unknown_tickers:
        warnings.append(
            f"Ignored saved weights for unknown tickers {', '.join(sorted(set(unknown_tickers)))}."
        )

    missing_tickers = [ticker for ticker in normalized_tickers if ticker not in filtered_weights]
    total_weight = sum(filtered_weights.values())
    if missing_tickers or total_weight <= 0:
        warnings.append(
            "Saved weights were incomplete, so the endpoint fell back to equal weights."
        )
        return fallback_weights, "equal_weight_fallback", warnings

    normalized_weights: Dict[str, float] = {}
    for ticker in normalized_tickers:
        normalized_weights[ticker] = round(filtered_weights[ticker] / total_weight, 4)

    drift = round(1.0 - sum(normalized_weights.values()), 4)
    if normalized_tickers and drift:
        last_ticker = normalized_tickers[-1]
        normalized_weights[last_ticker] = round(
            normalized_weights[last_ticker] + drift, 4
        )

    if abs(total_weight - 1.0) > 0.001:
        warnings.append("Saved weights were normalized to sum to 1.0.")

    return normalized_weights, "portfolio_metadata", warnings


def _classify_risk_profile(
    tickers: List[str],
    *,
    volatility: Optional[float],
    max_drawdown: Optional[float],
    beta: Optional[float],
    sharpe_ratio: Optional[float],
) -> Tuple[str, str, List[str], List[str]]:
    tickers_count = len(tickers)
    score = 0
    why: List[str] = []
    warnings: List[str] = []

    if tickers_count <= 2:
        score += 1
        warnings.append(f"Portfolio is concentrated across {tickers_count or 0} ticker(s).")
        why.append("Risk view uses an equal-weight assumption on a concentrated portfolio.")
    elif tickers_count >= 8:
        score -= 1
        why.append(f"Diversification improves with {tickers_count} tickers.")
    else:
        why.append(f"Portfolio spans {tickers_count} tickers under equal-weight assumptions.")

    if volatility is not None:
        if volatility >= 0.35:
            score += 2
            warnings.append(f"Realized volatility is elevated at {volatility:.2f}.")
            why.append("Realized volatility is firmly above the medium-risk band.")
        elif volatility >= 0.20:
            score += 1
            why.append(f"Realized volatility is moderate-to-high at {volatility:.2f}.")
        elif volatility <= 0.12:
            score -= 1
            why.append(f"Realized volatility is contained at {volatility:.2f}.")

    if beta is not None:
        if beta >= 1.20:
            score += 2
            warnings.append(f"Benchmark beta is elevated at {beta:.2f}.")
            why.append("Portfolio beta implies amplified moves versus the benchmark.")
        elif beta >= 0.90:
            score += 1
            why.append(f"Benchmark beta is near market sensitivity at {beta:.2f}.")
        elif beta <= 0.75:
            score -= 1
            why.append(f"Benchmark beta is defensive at {beta:.2f}.")

    if max_drawdown is not None:
        drawdown_abs = abs(max_drawdown)
        if drawdown_abs >= 0.25:
            score += 2
            warnings.append(f"Historical max drawdown reached {drawdown_abs:.2f}.")
            why.append("Historical drawdown is deep enough to warrant a high-risk flag.")
        elif drawdown_abs >= 0.12:
            score += 1
            why.append(f"Historical max drawdown reached {drawdown_abs:.2f}.")

    if sharpe_ratio is not None and sharpe_ratio < 0:
        score += 1
        warnings.append("Sharpe ratio is negative, which weakens risk-adjusted returns.")
        why.append("Risk-adjusted returns are currently negative.")

    if score <= 0:
        return "defensive", "low", why[:3], warnings
    if score <= 2:
        return "balanced", "medium", why[:3], warnings
    return "high_beta", "high", why[:3], warnings


class Portfolio(BaseModel):
    """Portfolio/Watchlist model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Portfolio name")
    description: str = Field(default="", description="Portfolio description")
    tickers: List[str] = Field(default_factory=list, description="List of ticker symbols")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PortfolioPerformance(BaseModel):
    """Portfolio performance metrics"""
    portfolio_id: str
    portfolio_name: str
    tickers_count: int
    total_return: Optional[float] = None
    avg_return: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    vs_benchmark: Optional[Dict[str, float]] = None
    calculated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PortfolioRiskProfile(BaseModel):
    """Portfolio state plus risk-profile snapshot."""

    portfolio: Dict[str, Any]
    benchmark: str
    weights: Dict[str, float] = Field(default_factory=dict)
    metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    risk_profile: str = "balanced"
    risk_level: str = "medium"
    risk: Dict[str, Any] = Field(default_factory=dict)
    why: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.45
    generated_at: str = Field(default_factory=_now_iso)
    source: List[str] = Field(
        default_factory=lambda: ["portfolio_service", "portfolio_risk_profile"]
    )
    error: Optional[str] = None


class PortfolioService:
    """Service for managing user portfolios/watchlists"""
    
    def __init__(self, storage_path: str = "data/user_portfolios.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_portfolios()
    
    def _load_portfolios(self) -> None:
        """Load portfolios from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.portfolios = {
                        portfolio_id: Portfolio(**portfolio_data)
                        for portfolio_id, portfolio_data in data.items()
                    }
                logger.info(f"Loaded {len(self.portfolios)} portfolios from storage")
            except Exception as e:
                logger.error(f"Error loading portfolios: {str(e)}")
                self.portfolios = {}
        else:
            self.portfolios = {}
            logger.info("No existing portfolios found, starting fresh")
    
    def _save_portfolios(self) -> None:
        """Save portfolios to storage"""
        try:
            data = {
                portfolio_id: portfolio.model_dump()
                for portfolio_id, portfolio in self.portfolios.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.portfolios)} portfolios to storage")
        except Exception as e:
            logger.error(f"Error saving portfolios: {str(e)}")
    
    def create_portfolio(
        self,
        name: str,
        description: str = "",
        tickers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Portfolio:
        """
        Create a new portfolio
        
        Args:
            name: Portfolio name
            description: Portfolio description
            tickers: Initial list of tickers
            metadata: Optional metadata
        
        Returns:
            Created portfolio
        """
        # Normalize tickers (uppercase, deduplicate)
        if tickers:
            tickers = list(set(t.upper() for t in tickers))
        else:
            tickers = []
        
        portfolio = Portfolio(
            name=name,
            description=description,
            tickers=tickers,
            metadata=metadata or {}
        )
        
        self.portfolios[portfolio.id] = portfolio
        self._save_portfolios()
        
        logger.info(f"Created portfolio {portfolio.id} '{name}' with {len(tickers)} tickers")
        return portfolio
    
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        return self.portfolios.get(portfolio_id)
    
    def list_portfolios(self) -> List[Portfolio]:
        """
        List all portfolios
        
        Returns:
            List of portfolios sorted by updated_at (newest first)
        """
        portfolios = list(self.portfolios.values())
        portfolios.sort(key=lambda p: p.updated_at, reverse=True)
        return portfolios
    
    def update_portfolio(
        self,
        portfolio_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Portfolio]:
        """
        Update a portfolio
        
        Args:
            portfolio_id: Portfolio ID
            name: New name (optional)
            description: New description (optional)
            tickers: New tickers list (optional)
            metadata: New metadata (optional)
        
        Returns:
            Updated portfolio or None if not found
        """
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return None
        
        # Update fields
        if name is not None:
            portfolio.name = name
        if description is not None:
            portfolio.description = description
        if tickers is not None:
            # Normalize tickers
            portfolio.tickers = list(set(t.upper() for t in tickers))
        if metadata is not None:
            portfolio.metadata = metadata
        
        portfolio.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._save_portfolios()
        logger.info(f"Updated portfolio {portfolio_id}")
        
        return portfolio
    
    def delete_portfolio(self, portfolio_id: str) -> bool:
        """
        Delete a portfolio
        
        Args:
            portfolio_id: Portfolio ID
        
        Returns:
            True if deleted, False if not found
        """
        if portfolio_id in self.portfolios:
            del self.portfolios[portfolio_id]
            self._save_portfolios()
            logger.info(f"Deleted portfolio {portfolio_id}")
            return True
        return False
    
    def add_tickers(
        self,
        portfolio_id: str,
        tickers: List[str]
    ) -> Optional[Portfolio]:
        """
        Add tickers to portfolio
        
        Args:
            portfolio_id: Portfolio ID
            tickers: List of tickers to add
        
        Returns:
            Updated portfolio or None if not found
        """
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return None
        
        # Normalize and deduplicate
        new_tickers = set(t.upper() for t in tickers)
        current_tickers = set(portfolio.tickers)
        
        # Add new tickers
        updated_tickers = current_tickers | new_tickers
        portfolio.tickers = sorted(list(updated_tickers))
        portfolio.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._save_portfolios()
        logger.info(f"Added {len(new_tickers)} tickers to portfolio {portfolio_id}")
        
        return portfolio
    
    def remove_tickers(
        self,
        portfolio_id: str,
        tickers: List[str]
    ) -> Optional[Portfolio]:
        """
        Remove tickers from portfolio
        
        Args:
            portfolio_id: Portfolio ID
            tickers: List of tickers to remove
        
        Returns:
            Updated portfolio or None if not found
        """
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return None
        
        # Normalize
        tickers_to_remove = set(t.upper() for t in tickers)
        current_tickers = set(portfolio.tickers)
        
        # Remove tickers
        updated_tickers = current_tickers - tickers_to_remove
        portfolio.tickers = sorted(list(updated_tickers))
        portfolio.updated_at = datetime.now(timezone.utc).isoformat()
        
        self._save_portfolios()
        logger.info(f"Removed {len(tickers_to_remove)} tickers from portfolio {portfolio_id}")
        
        return portfolio
    
    def get_performance(
        self,
        portfolio_id: str,
        benchmark: str = "SPY",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[PortfolioPerformance]:
        """
        Get portfolio performance metrics
        
        Args:
            portfolio_id: Portfolio ID
            benchmark: Benchmark ticker (default: SPY)
            start_date: Start date for calculation (YYYY-MM-DD), defaults to 1 year ago
            end_date: End date for calculation (YYYY-MM-DD), defaults to today
        
        Returns:
            Performance metrics or None if not found
        """
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return None
        
        if not portfolio.tickers:
            # Empty portfolio
            return PortfolioPerformance(
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                tickers_count=0,
                total_return=None,
                avg_return=None,
                volatility=None,
                sharpe_ratio=None,
                vs_benchmark={
                    "benchmark": benchmark,
                    "outperformance": None
                }
            )
        
        # Use performance service for real calculations
        try:
            perf_service = _get_performance_service()
            metrics, comparison, _ = perf_service.calculate_performance(
                tickers=portfolio.tickers,
                weights=None,  # Equal-weighted for now
                start_date=start_date,
                end_date=end_date,
                benchmark=benchmark
            )
            
            # Map to PortfolioPerformance model
            performance = PortfolioPerformance(
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                tickers_count=len(portfolio.tickers),
                total_return=metrics.total_return,
                avg_return=metrics.annualized_return,
                volatility=metrics.volatility,
                sharpe_ratio=metrics.sharpe_ratio,
                vs_benchmark={
                    "benchmark": comparison.benchmark_ticker,
                    "outperformance": comparison.outperformance
                }
            )
            
            logger.info(f"Calculated performance for portfolio {portfolio_id}")
            return performance
            
        except Exception as e:
            logger.error(f"Error calculating performance: {str(e)}")
            # Return structure with nulls on error
            return PortfolioPerformance(
                portfolio_id=portfolio.id,
                portfolio_name=portfolio.name,
                tickers_count=len(portfolio.tickers),
                total_return=None,
                avg_return=None,
                volatility=None,
                sharpe_ratio=None,
                vs_benchmark={
                    "benchmark": benchmark,
                    "outperformance": None
                }
            )

    def get_risk_profile(
        self,
        portfolio_id: str,
        benchmark: str = "SPY",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[PortfolioRiskProfile]:
        """Return a stable risk-profile snapshot for a persisted portfolio."""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return None

        tickers = sorted(portfolio.tickers)
        weights, weights_source, weight_warnings = _resolve_portfolio_weights(
            tickers,
            portfolio.metadata,
        )
        payload = PortfolioRiskProfile(
            portfolio={
                "id": portfolio.id,
                "name": portfolio.name,
                "description": portfolio.description,
                "tickers": tickers,
                "tickers_count": len(tickers),
                "updated_at": portfolio.updated_at,
            },
            benchmark=benchmark,
            weights=weights,
            filters_applied={
                "portfolio_id": portfolio.id,
                "benchmark": benchmark,
                "start_date": start_date,
                "end_date": end_date,
            },
            stats={
                "tickers_count": len(tickers),
                "equal_weight_assumption": weights_source != "portfolio_metadata",
                "weights_source": weights_source,
                "has_live_metrics": False,
                "non_null_metrics": 0,
            },
        )

        if not tickers:
            payload.risk_profile = "defensive"
            payload.risk_level = "low"
            payload.risk = {
                "level": "low",
                "caveat": "Portfolio has no holdings yet, so the profile is low-information.",
            }
            payload.why = [
                "No holdings are stored yet, so the endpoint returns an empty-state risk view."
            ]
            payload.warnings = [
                "Add at least one ticker to compute realized portfolio risk metrics."
            ]
            payload.confidence = 0.3
            return payload

        try:
            perf_service = _get_performance_service()
            metrics, comparison, _ = perf_service.calculate_performance(
                tickers=tickers,
                weights=weights,
                start_date=start_date,
                end_date=end_date,
                benchmark=benchmark,
            )

            raw_metrics = {
                "total_return": metrics.total_return,
                "annualized_return": metrics.annualized_return,
                "volatility": metrics.volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate,
                "beta": comparison.beta,
                "alpha": comparison.alpha,
                "correlation": comparison.correlation,
                "outperformance": comparison.outperformance,
            }
            non_null_metrics = sum(value is not None for value in raw_metrics.values())
            risk_profile, risk_level, why, warnings = _classify_risk_profile(
                tickers,
                volatility=metrics.volatility,
                max_drawdown=metrics.max_drawdown,
                beta=comparison.beta,
                sharpe_ratio=metrics.sharpe_ratio,
            )

            payload.metrics = raw_metrics
            payload.risk_profile = risk_profile
            payload.risk_level = risk_level
            payload.risk = {
                "level": risk_level,
                "caveat": (
                    warnings[0]
                    if warnings
                    else "Profile derived from saved portfolio weights and benchmark comparison."
                ),
            }
            payload.why = why or [
                "Risk profile derived from stored portfolio weights and benchmark comparison."
            ]
            payload.warnings = warnings + weight_warnings
            payload.stats = {
                "tickers_count": len(tickers),
                "equal_weight_assumption": weights_source != "portfolio_metadata",
                "weights_source": weights_source,
                "has_live_metrics": non_null_metrics > 0,
                "non_null_metrics": non_null_metrics,
                "largest_position_ticker": (
                    max(payload.weights, key=payload.weights.get)
                    if payload.weights
                    else None
                ),
                "largest_position_weight": (
                    max(payload.weights.values()) if payload.weights else None
                ),
            }
            payload.confidence = round(min(0.85, 0.35 + (0.05 * non_null_metrics)), 2)
            payload.generated_at = _now_iso()
            return payload
        except Exception as e:
            logger.error(f"Error calculating risk profile for {portfolio_id}: {str(e)}")
            risk_profile, risk_level, why, warnings = _classify_risk_profile(
                tickers,
                volatility=None,
                max_drawdown=None,
                beta=None,
                sharpe_ratio=None,
            )
            payload.risk_profile = risk_profile
            payload.risk_level = risk_level
            payload.risk = {
                "level": risk_level,
                "caveat": "Performance metrics unavailable; profile uses composition-only fallback.",
            }
            payload.why = why or [
                "Performance metrics were unavailable, so the profile falls back to holdings concentration only."
            ]
            payload.warnings = warnings + weight_warnings + [
                "Performance metrics unavailable; returned a composition-only fallback profile."
            ]
            payload.error = str(e)
            payload.confidence = 0.35
            payload.generated_at = _now_iso()
            payload.source.append("portfolio_risk_profile_fallback")
            return payload


# Singleton instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create portfolio service singleton"""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
