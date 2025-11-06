"""
Portfolio Service - Manage user portfolios/watchlists
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-PORTFOLIO-001 - Portfolio/Watchlist management
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


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
        benchmark: str = "SPY"
    ) -> Optional[PortfolioPerformance]:
        """
        Get portfolio performance metrics
        
        Args:
            portfolio_id: Portfolio ID
            benchmark: Benchmark ticker (default: SPY)
        
        Returns:
            Performance metrics or None if not found
        
        Note: This is a stub implementation. Real calculation would require
        fetching price data and computing returns, volatility, Sharpe ratio, etc.
        """
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            return None
        
        # TODO: Implement real performance calculation
        # This would require:
        # 1. Fetch historical price data for all tickers
        # 2. Calculate returns for each ticker
        # 3. Compute portfolio-level metrics
        # 4. Compare against benchmark
        
        # For now, return placeholder structure
        performance = PortfolioPerformance(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            tickers_count=len(portfolio.tickers),
            total_return=None,  # TODO: Calculate
            avg_return=None,  # TODO: Calculate
            volatility=None,  # TODO: Calculate
            sharpe_ratio=None,  # TODO: Calculate
            vs_benchmark={
                "benchmark": benchmark,
                "outperformance": None  # TODO: Calculate
            }
        )
        
        logger.info(f"Generated performance metrics for portfolio {portfolio_id}")
        return performance


# Singleton instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create portfolio service singleton"""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
