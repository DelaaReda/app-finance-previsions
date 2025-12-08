"""
Stock Screener Model
Task: FC-API-026 - Stocks Screener (advanced filtering)
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

class Sector(Enum):
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCIALS = "Financials"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    INDUSTRIALS = "Industrials"
    COMMUNICATION_SERVICES = "Communication Services"
    UTILITIES = "Utilities"
    REAL_ESTATE = "Real Estate"
    ENERGY = "Energy"
    MATERIALS = "Materials"

@dataclass
class StockFilter:
    """
    Model representing stock screener filters
    """
    sector: Optional[Sector] = None
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    pe_ratio_min: Optional[float] = None
    pe_ratio_max: Optional[float] = None
    pb_ratio_min: Optional[float] = None
    pb_ratio_max: Optional[float] = None
    dividend_yield_min: Optional[float] = None
    dividend_yield_max: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    volume_min: Optional[int] = None
    volatility: Optional[str] = None  # low, medium, high
    beta_min: Optional[float] = None
    beta_max: Optional[float] = None
    roe_min: Optional[float] = None  # Return on Equity
    eps_growth_min: Optional[float] = None  # Earnings Per Share growth
    debt_to_equity_min: Optional[float] = None
    debt_to_equity_max: Optional[float] = None
    target_tickers: Optional[List[str]] = None
    sort_by: str = "market_cap"  # Default sorting
    sort_order: str = "desc"  # asc or desc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Sector):
                    result[key] = value.value
                else:
                    result[key] = value
        return result

class StockScreener:
    """
    Service for screening stocks with advanced filtering capabilities
    """
    
    def __init__(self):
        self.filter_model = StockFilter()
        self.data_source = None  # To be connected to real data source later
    
    def validate_filter_params(self, filters: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate filter parameters and return any errors
        """
        errors = {}
        
        # Validate numeric ranges
        if filters.get('market_cap_min') is not None and filters.get('market_cap_max') is not None:
            if filters['market_cap_min'] > filters['market_cap_max']:
                errors['market_cap_range'] = 'market_cap_min must be less than market_cap_max'
        
        if filters.get('pe_ratio_min') is not None and filters.get('pe_ratio_max') is not None:
            if filters['pe_ratio_min'] > filters['pe_ratio_max']:
                errors['pe_ratio_range'] = 'pe_ratio_min must be less than pe_ratio_max'
        
        if filters.get('pb_ratio_min') is not None and filters.get('pb_ratio_max') is not None:
            if filters['pb_ratio_min'] > filters['pb_ratio_max']:
                errors['pb_ratio_range'] = 'pb_ratio_min must be less than pb_ratio_max'
        
        if filters.get('price_min') is not None and filters.get('price_max') is not None:
            if filters['price_min'] > filters['price_max']:
                errors['price_range'] = 'price_min must be less than price_max'
        
        if filters.get('volume_min') is not None and filters.get('volume_min') < 0:
            errors['volume_min'] = 'volume_min must be non-negative'
        
        # Validate volatility if provided
        volatility_valid = ["low", "medium", "high", None]
        if filters.get('volatility') not in volatility_valid:
            errors['volatility'] = 'volatility must be one of: low, medium, high'
        
        # Validate sort parameters
        valid_sort_by = ["market_cap", "pe_ratio", "dividend_yield", "price", "volume", "beta", "roe", "eps_growth", "last_update"]
        if filters.get('sort_by', 'market_cap') not in valid_sort_by:
            errors['sort_by'] = f'sort_by must be one of: {", ".join(valid_sort_by)}'
        
        valid_sort_order = ["asc", "desc"]
        if filters.get('sort_order', 'desc') not in valid_sort_order:
            errors['sort_order'] = f'sort_order must be one of: {", ".join(valid_sort_order)}'
        
        return errors
    
    def create_filtered_stock_list(self, stocks_data: List[Dict[str, Any]], filters: StockFilter) -> List[Dict[str, Any]]:
        """
        Apply filters to stock data and return filtered results
        """
        # Start with all stocks
        filtered_stocks = stocks_data[:]
        
        # Apply sector filter
        if filters.sector:
            sector_lower = filters.sector.value.lower()
            filtered_stocks = [
                stock for stock in filtered_stocks 
                if (stock.get("sector", "").lower() == sector_lower or 
                    stock.get("sector", "").lower() == filters.sector.value.replace(' ', '_').lower())
            ]
        
        # Apply market cap filters
        if filters.market_cap_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("market_cap") is not None and stock["market_cap"] >= filters.market_cap_min
            ]
        
        if filters.market_cap_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("market_cap") is not None and stock["market_cap"] <= filters.market_cap_max
            ]
        
        # Apply P/E ratio filters
        if filters.pe_ratio_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("pe_ratio") is not None and stock["pe_ratio"] >= filters.pe_ratio_min
            ]
        
        if filters.pe_ratio_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("pe_ratio") is not None and stock["pe_ratio"] <= filters.pe_ratio_max
            ]
        
        # Apply P/B ratio filters
        if filters.pb_ratio_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("pb_ratio") is not None and stock["pb_ratio"] >= filters.pb_ratio_min
            ]
        
        if filters.pb_ratio_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("pb_ratio") is not None and stock["pb_ratio"] <= filters.pb_ratio_max
            ]
        
        # Apply dividend yield filters
        if filters.dividend_yield_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("dividend_yield") is not None and stock["dividend_yield"] >= filters.dividend_yield_min
            ]
        
        if filters.dividend_yield_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("dividend_yield") is not None and stock["dividend_yield"] <= filters.dividend_yield_max
            ]
        
        # Apply price filters
        if filters.price_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("current_price") is not None and stock["current_price"] >= filters.price_min
            ]
        
        if filters.price_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("current_price") is not None and stock["current_price"] <= filters.price_max
            ]
        
        # Apply volume filter
        if filters.volume_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("volume") is not None and stock["volume"] >= filters.volume_min
            ]
        
        # Apply beta filters
        if filters.beta_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("beta") is not None and stock["beta"] >= filters.beta_min
            ]
        
        if filters.beta_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("beta") is not None and stock["beta"] <= filters.beta_max
            ]
        
        # Apply RoE (Return on Equity) filter
        if filters.roe_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("roe") is not None and stock["roe"] >= filters.roe_min
            ]
        
        # Apply EPS growth filter
        if filters.eps_growth_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("eps_growth") is not None and stock["eps_growth"] >= filters.eps_growth_min
            ]
        
        # Apply Debt-to-Equity filters
        if filters.debt_to_equity_min is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("debt_to_equity") is not None and stock["debt_to_equity"] >= filters.debt_to_equity_min
            ]
        
        if filters.debt_to_equity_max is not None:
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("debt_to_equity") is not None and stock["debt_to_equity"] <= filters.debt_to_equity_max
            ]
        
        # Apply target tickers filter
        if filters.target_tickers:
            ticker_set = {t.upper() for t in filters.target_tickers}
            filtered_stocks = [
                stock for stock in filtered_stocks
                if stock.get("ticker", "").upper() in ticker_set
            ]
        
        # Apply volatility filter
        if filters.volatility:
            if filters.volatility == "low":
                filtered_stocks = [stock for stock in filtered_stocks if stock.get("volatility") and stock["volatility"] < 0.15]
            elif filters.volatility == "medium":
                filtered_stocks = [stock for stock in filtered_stocks if stock.get("volatility") and 0.15 <= stock["volatility"] < 0.30]
            elif filters.volatility == "high":
                filtered_stocks = [stock for stock in filtered_stocks if stock.get("volatility") and stock["volatility"] >= 0.30]
        
        # Sort the results
        reverse_sort = filters.sort_order == "desc"
        
        if filters.sort_by == "market_cap":
            filtered_stocks.sort(key=lambda x: x.get("market_cap", 0), reverse=reverse_sort)
        elif filters.sort_by == "pe_ratio":
            filtered_stocks.sort(key=lambda x: x.get("pe_ratio", float('inf')) if x.get("pe_ratio") is not None else float('inf'), reverse=reverse_sort)
        elif filters.sort_by == "dividend_yield":
            filtered_stocks.sort(key=lambda x: x.get("dividend_yield", 0) if x.get("dividend_yield") is not None else 0, reverse=reverse_sort)
        elif filters.sort_by == "price":
            filtered_stocks.sort(key=lambda x: x.get("current_price", 0) if x.get("current_price") is not None else 0, reverse=reverse_sort)
        elif filters.sort_by == "volume":
            filtered_stocks.sort(key=lambda x: x.get("volume", 0) if x.get("volume") is not None else 0, reverse=reverse_sort)
        elif filters.sort_by == "beta":
            filtered_stocks.sort(key=lambda x: x.get("beta", 0) if x.get("beta") is not None else 0, reverse=reverse_sort)
        elif filters.sort_by == "roe":
            filtered_stocks.sort(key=lambda x: x.get("roe", 0) if x.get("roe") is not None else 0, reverse=reverse_sort)
        elif filters.sort_by == "eps_growth":
            filtered_stocks.sort(key=lambda x: x.get("eps_growth", 0) if x.get("eps_growth") is not None else 0, reverse=reverse_sort)
        else:  # Default to market_cap
            filtered_stocks.sort(key=lambda x: x.get("market_cap", 0), reverse=reverse_sort)
        
        return filtered_stocks
    
    def screen_stocks(self, stocks_data: List[Dict[str, Any]], filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main screening method that validates filters and applies them to stock data
        """
        # Validate filter parameters
        validation_errors = self.validate_filter_params(filter_dict)
        if validation_errors:
            return {
                "ok": False,
                "error": "Invalid filter parameters",
                "validation_errors": validation_errors,
                "filtered_stocks": [],
                "count": 0,
                "applied_filters": {},
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        # Create StockFilter object from dict
        try:
            # Create filter object with default values, but handle enums properly
            filter_kwargs = {}
            for key, value in filter_dict.items():
                if key == 'sector' and value:
                    try:
                        filter_kwargs[key] = Sector(value)
                    except ValueError:
                        filter_kwargs[key] = Sector.TECHNOLOGY  # Default to technology
                elif value is not None:
                    filter_kwargs[key] = value
            
            # Set defaults for missing values
            if 'sort_by' not in filter_kwargs:
                filter_kwargs['sort_by'] = 'market_cap'
            if 'sort_order' not in filter_kwargs:
                filter_kwargs['sort_order'] = 'desc'
                
            filters = StockFilter(**filter_kwargs)
        except TypeError as e:
            return {
                "ok": False,
                "error": f"Invalid filter format: {str(e)}",
                "filtered_stocks": [],
                "count": 0,
                "applied_filters": {},
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        # Apply filters to the stock data
        filtered_results = self.create_filtered_stock_list(stocks_data, filters)
        
        return {
            "ok": True,
            "data": {
                "filtered_stocks": filtered_results,
                "count": len(filtered_results),
                "applied_filters": filter_dict,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "filter_summary": {
                    "sector": filter_dict.get('sector'),
                    "price_range": [filter_dict.get('price_min'), filter_dict.get('price_max')],
                    "market_cap_range": [filter_dict.get('market_cap_min'), filter_dict.get('market_cap_max')],
                    "pe_ratio_range": [filter_dict.get('pe_ratio_min'), filter_dict.get('pe_ratio_max')],
                    "sort_by": filter_dict.get('sort_by', 'market_cap'),
                    "sort_order": filter_dict.get('sort_order', 'desc')
                }
            }
        }