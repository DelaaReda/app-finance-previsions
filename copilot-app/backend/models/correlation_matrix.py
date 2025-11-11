"""
Correlation Matrix Model - Finance Copilot System
Provides data structure for stock correlation matrices with validation and formatting
Task: FC-API-027 - Stock Correlation Heatmap - ALEX-FINANCE-ANALYST-SUPERMAN-29  
"""
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


class CorrelationMatrixModel:
    """
    Model for correlation matrix with validation and formatting for frontend visualization
    """
    
    def __init__(self):
        self.created_at = datetime.now()
    
    def validate_correlation_value(self, value: Union[float, int]) -> bool:
        """
        Validate that correlation value is in valid range [-1.0, 1.0]
        
        Args:
            value: Correlation coefficient to validate
        
        Returns:
            Boolean indicating if value is valid
        """
        try:
            num_value = float(value)
            return -1.0 <= num_value <= 1.0
        except (TypeError, ValueError):
            return False
    
    def create_correlation_matrix(
        self, 
        ticker_returns: Dict[str, List[float]], 
        method: str = "pearson"
    ) -> Dict[str, Any]:
        """
        Create correlation matrix from ticker returns data
        
        Args:
            ticker_returns: Dictionary with ticker as key and list of returns as value
            method: Correlation method (pearson, spearman, kendall)
        
        Returns:
            Dictionary containing correlation matrix and metadata
        """
        if not ticker_returns:
            return self._create_empty_matrix([], datetime.now(), datetime.now())
        
        # Filter to include only tickers with sufficient data
        valid_tickers = []
        valid_returns = {}
        
        for ticker, returns in ticker_returns.items():
            if len(returns) >= 2:  # Need at least 2 points to calculate correlation
                valid_tickers.append(ticker)
                valid_returns[ticker] = returns
        
        if len(valid_returns) < 2:
            return self._create_empty_matrix(valid_tickers, datetime.now(), datetime.now())
        
        # Align all return series to same length (take minimum)
        min_length = min(len(returns) for returns in valid_returns.values()) if valid_returns else 0
        aligned_returns = {ticker: returns[:min_length] for ticker, returns in valid_returns.items()}
        
        # Create DataFrame for correlation calculation
        df = pd.DataFrame(aligned_returns)
        
        # Calculate correlation matrix using specified method
        try:
            if method.lower() == "pearson":
                correlation_matrix = df.corr(method="pearson")
            elif method.lower() == "spearman":
                correlation_matrix = df.corr(method="spearman")
            elif method.lower() == "kendall":
                correlation_matrix = df.corr(method="kendall") 
            else:
                correlation_matrix = df.corr(method="pearson")  # Default to pearson
        except Exception as e:
            # If correlation calculation fails, return empty matrix
            return self._create_empty_matrix(valid_tickers, datetime.now(), datetime.now())
        
        # Calculate data points per symbol to use in metadata
        data_points_per_symbol = min(len(returns) for returns in aligned_returns.values()) if aligned_returns else 0
        
        # Convert to the format expected by frontend (for Tremor heatmaps)
        matrix_data = self._format_for_frontend(correlation_matrix, valid_tickers)
        
        # Calculate metadata
        start_date = (datetime.now() - timedelta(days=data_points_per_symbol)).isoformat() if data_points_per_symbol > 0 else datetime.now().isoformat()
        end_date = datetime.now().isoformat()
        
        return {
            "matrix": matrix_data["matrix_dict"],
            "matrix_table": matrix_data["matrix_table"],  # For Tremor heatmap
            "tickers": valid_tickers,
            "rows": valid_tickers,
            "columns": valid_tickers,
            "method": method,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "symbols_count": len(valid_tickers),
                "data_points_per_symbol": data_points_per_symbol,
                "computation_method": method,
                "correlation_range": {
                    "min": float(correlation_matrix.min().min()) if not correlation_matrix.empty else 0.0,
                    "max": float(correlation_matrix.max().max()) if not correlation_matrix.empty else 0.0,
                    "avg": float(correlation_matrix.mean().mean()) if not correlation_matrix.empty else 0.0
                },
                "valid_pairs": self._count_valid_correlations(correlation_matrix)
            },
            "source": ["correlation_model", "financial_analysis", "matrix_computation"]
        }
    
    def _format_for_frontend(self, correlation_df: pd.DataFrame, tickers: List[str]) -> Dict[str, Any]:
        """
        Format correlation matrix for frontend consumption (especially Tremor heatmaps)
        
        Args:
            correlation_df: Pandas DataFrame with correlation values
            tickers: List of tickers in the matrix
        
        Returns:
            Dictionary with formatted data for frontend
        """
        # Convert to nested dictionary format
        matrix_dict = {}
        for i, row_ticker in enumerate(tickers):
            matrix_dict[row_ticker] = {}
            for j, col_ticker in enumerate(tickers):
                # Get correlation value and ensure it's in valid range
                val = correlation_df.iloc[i, j]
                if pd.isna(val):
                    val = 0.0  # Default to 0 if NaN
                elif val < -1.0:
                    val = -1.0
                elif val > 1.0:
                    val = 1.0
                
                matrix_dict[row_ticker][col_ticker] = float(val)
        
        # Convert to table format for Tremor Heatmap component
        matrix_table = []
        for i, row_ticker in enumerate(tickers):
            row_data = {"name": row_ticker}  # Tremor expects 'name' for row identifier
            for j, col_ticker in enumerate(tickers):
                val = correlation_df.iloc[i, j]
                if pd.isna(val):
                    val = 0.0
                elif val < -1.0:
                    val = -1.0
                elif val > 1.0:
                    val = 1.0
                
                # Use the column ticker as the key for that value
                row_data[col_ticker] = float(val)
            matrix_table.append(row_data)
        
        return {
            "matrix_dict": matrix_dict,
            "matrix_table": matrix_table
        }
    
    def _create_empty_matrix(self, tickers: List[str], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Create empty matrix structure when insufficient data is available
        
        Args:
            tickers: List of tickers that were requested
            start_date: Start date of the requested period
            end_date: End date of the requested period
        
        Returns:
            Empty matrix structure with metadata
        """
        # Create empty matrix structure
        empty_matrix = {}
        for ticker in tickers:
            empty_matrix[ticker] = {}
            for other_ticker in tickers:
                empty_matrix[ticker][other_ticker] = 0.0  # Default to 0 correlation
        
        # Create empty table format
        empty_table = []
        for ticker in tickers:
            row_data = {"name": ticker}
            for other_ticker in tickers:
                row_data[other_ticker] = 0.0
            empty_table.append(row_data)
        
        return {
            "matrix": empty_matrix,
            "matrix_table": empty_table,
            "tickers": tickers,
            "rows": tickers,
            "columns": tickers,
            "method": "pearson",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "message": "Insufficient data for correlation calculation - matrix contains defaults",
            "metadata": {
                "symbols_count": len(tickers),
                "data_points_per_symbol": 0,
                "computation_method": "default_zero",
                "correlation_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
                "valid_pairs": 0
            },
            "source": ["correlation_model", "fallback_empty", "insufficient_data"]
        }
    
    def _count_valid_correlations(self, corr_matrix: pd.DataFrame) -> int:
        """
        Count number of valid (non-NaN) correlation values in the matrix
        
        Args:
            corr_matrix: Correlation matrix as pandas DataFrame
        
        Returns:
            Number of valid correlation values
        """
        if corr_matrix.empty:
            return 0
        
        # Count non-NaN values
        valid_count = (~corr_matrix.isna()).sum().sum()
        
        # Subtract diagonal since correlation of self with self is always 1.0 (not meaningful)
        n = len(corr_matrix)
        valid_count -= n  # subtract diagonal
        
        return int(valid_count)
    
    def get_correlation_strength_label(self, correlation_value: float) -> str:
        """
        Get human-readable label for correlation strength
        
        Args:
            correlation_value: Correlation coefficient (-1.0 to 1.0)
        
        Returns:
            String label describing the strength
        """
        abs_value = abs(correlation_value)
        if abs_value >= 0.7:
            return "Very Strong"
        elif abs_value >= 0.5:
            return "Strong"
        elif abs_value >= 0.3:
            return "Moderate"
        elif abs_value >= 0.1:
            return "Weak"
        else:
            return "Negligible"


# Global instance
correlation_model = CorrelationMatrixModel()