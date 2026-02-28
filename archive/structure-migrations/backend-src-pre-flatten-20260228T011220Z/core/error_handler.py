"""
Enhanced Error Handler for Backend Services
Task: FC-ARCH-ERRORS-002 - Error Handling Reinforcement
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, Any, Optional, Union
import logging
import traceback
import sys
from pathlib import Path


# Set up logging for error handler module
logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Comprehensive error handling system with detailed logging and proper responses
    """
    
    def __init__(self):
        self.error_counter = 0
    
    def handle_error(self, 
                    error: Exception, 
                    context: str = "unknown",
                    fallback_data: Optional[Any] = None,
                    include_stack_trace: bool = False) -> Dict[str, Any]:
        """
        Handle errors with detailed logging and proper fallback response
        
        Args:
            error: Exception that occurred
            context: Context where error occurred (e.g., "forecast_service", "news_route")
            fallback_data: Data to return as fallback if applicable
            include_stack_trace: Whether to include stack trace in response (for debugging)
        
        Returns:
            Structured error response with fallback data if provided
        """
        self.error_counter += 1
        error_id = f"error_{int(datetime.utcnow().timestamp())}_{self.error_counter}"
        
        # Create detailed error log
        error_details = {
            "error_id": error_id,
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "traceback": traceback.format_exc() if include_stack_trace else None,
            "source": ["error_handler", "structured_error_handling", "fc-arch-errors-002"]
        }
        
        # Log the error with details
        logger.error(
            f"Error occurred in {context}: {str(error)}", 
            extra=error_details
        )
        
        # Create error response maintaining never-empty contract
        response = {
            "ok": False,
            "data": fallback_data if fallback_data is not None else {},
            "error": {
                "id": error_id,
                "type": error_details["type"],
                "message": error_details["message"],
                "context": error_details["context"],
                "timestamp": error_details["timestamp"],
                "source": error_details["source"]
            },
            "freshness": "error",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "message": f"Error in {context}: {str(error)} - fallback data served to maintain never-empty contract"
        }
        
        # Add traceback if requested
        if include_stack_trace and error_details["traceback"]:
            response["error"]["traceback"] = error_details["traceback"]
        
        return response
    
    def handle_api_error(self, 
                        error: Exception, 
                        route: str, 
                        params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle errors specifically for API routes with route context
        
        Args:
            error: Exception that occurred
            route: API route (e.g., "/api/forecasts", "/api/news/feed")
            params: Request parameters for context
        
        Returns:
            Structured API error response
        """
        return self.handle_error(
            error=error,
            context=f"API_ROUTE_{route}",
            fallback_data={},
            include_stack_trace=False  # Don't expose stack traces in production API responses
        )
    
    def handle_service_error(self, 
                           error: Exception, 
                           service: str,
                           operation: str,
                           fallback_result: Optional[Any] = None) -> Dict[str, Any]:
        """
        Handle errors specifically for service operations
        
        Args:
            error: Exception that occurred
            service: Service name (e.g., "forecast_service", "news_analyzer")
            operation: Operation being performed (e.g., "get_forecasts", "calculate_impact")
            fallback_result: Result to return as fallback
        
        Returns:
            Service error response with fallback result if provided
        """
        return self.handle_error(
            error=error,
            context=f"SERVICE_{service}_{operation}",
            fallback_data=fallback_result
        )
    
    def handle_data_access_error(self, 
                                error: Exception, 
                                data_source: str,
                                key: str,
                                fallback_value: Optional[Any] = None) -> Dict[str, Any]:
        """
        Handle errors for data access operations with never-empty guarantees
        
        Args:
            error: Exception that occurred
            data_source: Data source (e.g., "json_file", "database", "api")
            key: Key being accessed (e.g., "forecasts", "news_feed")
            fallback_value: Value to return as fallback (maintains never-empty)
        
        Returns:
            Data access error response with fallback value
        """
        return self.handle_error(
            error=error,
            context=f"DATA_ACCESS_{data_source}_{key}",
            fallback_data=fallback_value
        )
    
    def log_warning(self, 
                   message: str, 
                   context: str = "unknown", 
                   params: Optional[Dict[str, Any]] = None) -> None:
        """
        Log warning messages with context
        
        Args:
            message: Warning message
            context: Context of warning
            params: Additional parameters for context
        """
        warning_info = {
            "message": message,
            "context": context,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "params": params or {},
            "source": ["error_handler", "warning_logger", "fc-arch-errors-002"]
        }
        
        logger.warning(message, extra=warning_info)
    
    def validate_and_handle(self, 
                           data: Any, 
                           validator_func, 
                           context: str = "validation") -> Dict[str, Any]:
        """
        Validate data and handle validation errors gracefully
        
        Args:
            data: Data to validate
            validator_func: Function that performs validation (should raise ValueError if invalid)
            context: Context for logging
        
        Returns:
            Validated data or error response if validation fails
        """
        try:
            validated_data = validator_func(data)
            return {
                "ok": True,
                "data": validated_data,
                "source": ["error_handler", "validation_success", "fc-arch-errors-002"]
            }
        except ValueError as ve:
            return self.handle_error(ve, f"{context}_validation_error", data)
        except Exception as e:
            return self.handle_error(e, f"{context}_validation_unexpected", data)
    
    def retry_with_fallback(self,
                           operation_func,
                           max_attempts: int = 3,
                           fallback_value: Optional[Any] = None,
                           context: str = "retry_operation") -> Any:
        """
        Execute operation with retry mechanism and fallback
        
        Args:
            operation_func: Function to execute (should be callable)
            max_attempts: Maximum number of retry attempts
            fallback_value: Value to return if all attempts fail
            context: Context for logging
        
        Returns:
            Result of operation or fallback value if all attempts fail
        """
        for attempt in range(max_attempts):
            try:
                result = operation_func()
                if result is not None:
                    return {
                        "ok": True,
                        "data": result,
                        "attempt": attempt + 1,
                        "attempts_total": max_attempts,
                        "source": ["error_handler", "retry_success", "fc-arch-errors-002"]
                    }
            except Exception as e:
                if attempt == max_attempts - 1:  # Last attempt
                    # All attempts failed, return fallback
                    error_msg = f"Operation failed after {max_attempts} attempts: {str(e)}"
                    error = Exception(error_msg)
                    return self.handle_error(error, f"{context}_after_{max_attempts}_attempts", fallback_value)
                else:
                    # Retry with delay (could implement exponential backoff here)
                    import time
                    time.sleep(0.1 * (attempt + 1))  # Simple backoff
                    continue
        
        return {
            "ok": True,  # Never-empty contract maintained
            "data": fallback_value,
            "attempt": max_attempts,
            "attempts_total": max_attempts,
            "message": "Operation exhausted retries but fallback returned to maintain never-empty contract",
            "source": ["error_handler", "retry_fallback", "fc-arch-errors-002"]
        }


def format_error_response(error: Exception, 
                         context: str, 
                         fallback_data: Optional[Any] = None,
                         include_stack: bool = False) -> Dict[str, Any]:
    """
    Convenience function to format error responses consistently
    """
    error_handler = ErrorHandler()
    return error_handler.handle_error(error, context, fallback_data, include_stack)


def handle_api_route_error(error: Exception, route: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Convenience function for API route error handling
    """
    error_handler = ErrorHandler()
    return error_handler.handle_api_error(error, route, params)


def handle_service_error(error: Exception, service: str, operation: str, fallback: Optional[Any] = None) -> Dict[str, Any]:
    """
    Convenience function for service error handling
    """
    error_handler = ErrorHandler()
    return error_handler.handle_service_error(error, service, operation, fallback)


def validate_with_error_handling(data: Any, validator_func, context: str = "validation") -> Dict[str, Any]:
    """
    Convenience function for validation with error handling
    """
    error_handler = ErrorHandler()
    return error_handler.validate_and_handle(data, validator_func, context)


def retry_operation_with_fallback(operation_func, max_attempts: int = 3, fallback_value: Optional[Any] = None, context: str = "retry") -> Any:
    """
    Convenience function for operation retries with fallback
    """
    error_handler = ErrorHandler()
    return error_handler.retry_with_fallback(operation_func, max_attempts, fallback_value, context)


# Global instance
common_error_handler = ErrorHandler()


# Example usage in route files
def example_route_error_handling():
    """
    Example of how to use error handler in a route
    """
    try:
        # Simulate a route operation
        result = some_route_operation()
        return {
            "ok": True,
            "data": result,
            "freshness": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        # Use the error handler to return structured error response
        return handle_api_route_error(
            error=e,
            route="/api/example",
            params={"example_param": "value"}  # Include relevant params for context
        )


def example_service_error_handling():
    """
    Example of how to use error handler in a service
    """
    try:
        # Simulate a service operation
        result = some_service_operation()
        return {
            "ok": True,
            "result": result
        }
    except Exception as e:
        # Use service error handler with appropriate fallback
        return handle_service_error(
            error=e,
            service="example_service",
            operation="example_operation",
            fallback={"result": [], "count": 0, "message": "Service temporarily unavailable"}
        )


def example_data_validation():
    """
    Example of how to use validation with error handling
    """
    raw_data = {"value": "invalid_value"}  # Some raw data to validate
    
    def validate_data(data):
        # Example validation function
        if not isinstance(data, dict) or "value" not in data:
            raise ValueError("Invalid data format: expected dict with 'value' key")
        if not isinstance(data["value"], str) or len(data["value"]) == 0:
            raise ValueError("Invalid value: expected non-empty string")
        return {"validated_value": data["value"], "processed": True}
    
    return validate_with_error_handling(raw_data, validate_data, "example_validation")