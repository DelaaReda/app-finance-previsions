"""
Universal Search Service
Task: FC-API-035 - Universal Search Implementation
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from models.search_result import universal_search_index, SearchResultSet, SearchResultType
from storage.io import load_json
from services.cache_layer import load_or_compute


class UniversalSearchService:
    """
    Service for universal search across all data domains (stocks, news, forecasts, briefs)
    """
    
    def __init__(self):
        self.search_index = universal_search_index
        self._initialize_index()
    
    def _initialize_index(self):
        """
        Initialize the search index with existing data
        """
        try:
            # Load and index forecasts
            self._index_forecasts()
            
            # Load and index news
            self._index_news()
            
            # Load and index briefs
            self._index_briefs()
            
            # Load and index macro data
            self._index_macro_data()
            
            print(f"Search index initialized with {len(self.search_index.documents)} documents")
        except Exception as e:
            print(f"Error initializing search index: {str(e)}")
    
    def _index_forecasts(self):
        """
        Index forecast data for search
        """
        try:
            forecasts_data = load_json("forecasts") or {}
            
            forecasts = (forecasts_data.get("data", {}).get("rows", []) or 
                        forecasts_data.get("rows", []) or 
                        forecasts_data.get("payload", {}).get("rows", []) or
                        [])
            
            for i, forecast in enumerate(forecasts):
                if isinstance(forecast, dict):
                    # Create search document for each forecast
                    doc_id = f"forecast_{forecast.get('id', str(i))}"
                    
                    # Create content string from relevant fields
                    content_parts = []
                    if forecast.get("ticker"):
                        content_parts.append(f"Ticker: {forecast['ticker']}")
                    if forecast.get("direction"):
                        content_parts.append(f"Direction: {forecast['direction']}")
                    if forecast.get("expected_return"):
                        content_parts.append(f"Expected Return: {forecast['expected_return']}")
                    if forecast.get("confidence"):
                        content_parts.append(f"Confidence: {forecast['confidence']}")
                    if forecast.get("horizon"):
                        content_parts.append(f"Horizon: {forecast['horizon']}")
                    if forecast.get("model_version"):
                        content_parts.append(f"Model: {forecast['model_version']}")
                    if forecast.get("model_source"):
                        content_parts.append(f"Source: {forecast['model_source']}")
                    
                    content = " ".join(content_parts)
                    
                    # Create tags from forecast properties
                    tags = []
                    if forecast.get("ticker"):
                        tags.append(f"ticker:{forecast['ticker'].upper()}")
                    if forecast.get("horizon"):
                        tags.append(f"horizon:{forecast['horizon']}")
                    if forecast.get("direction"):
                        tags.append(f"direction:{forecast['direction']}")
                    if forecast.get("model_source"):
                        tags.append(f"model:{forecast['model_source']}")
                    
                    self.search_index.add_document(
                        doc_id=doc_id,
                        content=content,
                        doc_type=SearchResultType.FORECAST,
                        ticker=forecast.get("ticker"),
                        source=forecast.get("model_source") or "forecast_ml_model",
                        title=f"Forecast for {forecast.get('ticker', 'UNKNOWN')} - {forecast.get('horizon', 'unknown')}",
                        url=f"/forecasts#{forecast.get('ticker', '')}",
                        summary=f"Expected return: {forecast.get('expected_return', 0):.2%} over {forecast.get('horizon', 'unknown period')}",
                        timestamp=forecast.get("calculation_timestamp") or forecast.get("generated_at") or datetime.utcnow().isoformat() + "Z",
                        tags=tags
                    )
        except Exception as e:
            print(f"Error indexing forecasts: {str(e)}")
    
    def _index_news(self):
        """
        Index news data for search
        """
        try:
            news_data = load_json("news_feed") or {}
            
            articles = (news_data.get("data", {}).get("articles", []) or 
                       news_data.get("articles", []) or 
                       news_data.get("payload", {}).get("articles", []) or
                       [])
            
            for i, article in enumerate(articles):
                if isinstance(article, dict):
                    doc_id = f"news_{article.get('id', str(i))}"
                    
                    # Create content from title, description, and content
                    title = article.get("title", "")
                    description = article.get("description", article.get("summary", ""))
                    content_body = article.get("content", "")
                    
                    content = f"{title} {description} {content_body}".strip()
                    
                    # Extract tickers mentioned in the article
                    tickers = self._extract_tickers(content)
                    
                    # Create tags
                    tags = ["news"]
                    if article.get("source"):
                        tags.append(f"source:{article['source']}")
                    if article.get("category"):
                        tags.append(f"category:{article['category']}")
                    for ticker in tickers:
                        tags.append(f"ticker:{ticker}")
                    
                    self.search_index.add_document(
                        doc_id=doc_id,
                        content=content,
                        doc_type=SearchResultType.NEWS,
                        ticker=tickers[0] if tickers else None,  # Use first ticker as primary ticker
                        source=article.get("source") or "unknown_news_source",
                        title=title,
                        url=article.get("link") or article.get("url"),
                        summary=description[:200] + "..." if len(description) > 200 else description,
                        timestamp=article.get("pubDate") or article.get("publishedAt") or article.get("timestamp") or datetime.utcnow().isoformat() + "Z",
                        tags=tags
                    )
        except Exception as e:
            print(f"Error indexing news: {str(e)}")
    
    def _index_briefs(self):
        """
        Index market brief data for search
        """
        try:
            brief_data = load_json("brief_weekly") or {}
            
            # Index brief content
            if brief_data:
                doc_id = f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Extract key information from brief
                content_parts = []
                
                # Add top signals
                top_signals = brief_data.get("top_signals", brief_data.get("top_3_signals", []))
                for signal in top_signals:
                    if isinstance(signal, dict):
                        content_parts.append(str(signal.get("title", "")))
                        content_parts.append(str(signal.get("description", "")))
                        content_parts.append(str(signal.get("details", "")))
                
                # Add market regime
                if "market_regime" in brief_data:
                    content_parts.append(f"Market Regime: {brief_data['market_regime']}")
                
                # Add top risks
                top_risks = brief_data.get("top_3_risks", brief_data.get("top_risks", []))
                for risk in top_risks:
                    if isinstance(risk, dict):
                        content_parts.append(str(risk.get("title", "")))
                        content_parts.append(str(risk.get("description", "")))
                
                content = " ".join(content_parts)
                
                # Extract tickers mentioned in brief
                brief_tickers = self._extract_tickers(content)
                
                # Create tags
                tags = ["brief", "market_analysis"]
                for ticker in brief_tickers:
                    tags.append(f"ticker:{ticker}")
                
                self.search_index.add_document(
                    doc_id=doc_id,
                    content=content,
                    doc_type=SearchResultType.BRIEF,
                    ticker=brief_tickers[0] if brief_tickers else None,
                    source="weekly_brief_ml_analysis",
                    title=f"Weekly Brief - {datetime.now().strftime('%Y-%m-%d')}",
                    url="/brief",
                    summary="Weekly market analysis and key signals",
                    timestamp=brief_data.get("generated_at") or datetime.utcnow().isoformat() + "Z",
                    tags=tags
                )
        except Exception as e:
            print(f"Error indexing briefs: {str(e)}")
    
    def _index_macro_data(self):
        """
        Index macro data for search
        """
        try:
            macro_data = load_json("macro_series") or {}
            
            if macro_data:
                doc_id = f"macro_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Extract key information from macro data
                content_parts = []
                
                # Add key series data
                for key, value in macro_data.items():
                    if isinstance(value, (int, float, str)):
                        content_parts.append(f"{key}: {value}")
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            content_parts.append(f"{sub_key}: {sub_value}")
                    elif isinstance(value, list) and value:
                        # Include recent observations
                        for obs in value[:5]:  # Only include first 5 observations
                            if isinstance(obs, dict):
                                for obs_key, obs_val in obs.items():
                                    content_parts.append(f"{obs_key}: {obs_val}")
                
                content = " ".join(content_parts)
                
                # Extract any tickers or economic indicators from content
                extracted_items = self._extract_tickers(content)
                
                # Create tags
                tags = ["macro", "economic_data"]
                for item in extracted_items:
                    tags.append(f"indicator:{item}")
                
                self.search_index.add_document(
                    doc_id=doc_id,
                    content=content,
                    doc_type=SearchResultType.MACRO,
                    ticker=extracted_items[0] if extracted_items else None,
                    source="macro_economic_data",
                    title="Macro Economic Data",
                    url="/macro",
                    summary="Economic indicators and macro data series",
                    timestamp=macro_data.get("generated_at") or datetime.utcnow().isoformat() + "Z",
                    tags=tags
                )
        except Exception as e:
            print(f"Error indexing macro data: {str(e)}")
    
    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract potential ticker symbols from text
        """
        import re
        # Look for uppercase letter sequences that might be tickers
        potential_tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
        
        # Filter out common non-ticker words
        common_words = {
            'THE', 'AND', 'FOR', 'NOT', 'HAS', 'HAD', 'GET', 'CAN', 'NOW', 'NEW', 'END', 'SET', 
            'RUN', 'LET', 'ALL', 'ANY', 'EACH', 'EVERY', 'MORE', 'MOST', 'OTHER', 'SOME', 
            'SUCH', 'NO', 'ONLY', 'OWN', 'SAME', 'SO', 'THAN', 'TOO', 'VERY', 'JUST', 
            'COME', 'GIVE', 'LIVE', 'MOVE', 'PUT', 'SEE', 'SEEM', 'TRY', 'TURN', 'USE', 
            'WORK', 'ACT', 'BAD', 'BUSY', 'COLD', 'COOL', 'DUE', 'EARLY', 'EASY', 'FREE', 
            'GOOD', 'HOT', 'HUGE', 'IDEA', 'MAD', 'MAIN', 'NICE', 'OKAY', 'OPEN', 'REAL', 
            'SAFE', 'SLOW', 'SURE', 'TINY', 'TRUE', 'WARM', 'WAY', 'WILD', 'YOUNG', 'TOP', 
            'LOT', 'DAY', 'AGO', 'HOUR', 'MIN'
        }
        
        # Return unique tickers that aren't common words
        tickers = list(set(ticker for ticker in potential_tickers if ticker.upper() not in common_words and len(ticker) >= 2))
        return tickers
    
    def universal_search(self,
                        query: str,
                        types: Optional[List[str]] = None,
                        tickers: Optional[List[str]] = None,
                        sources: Optional[List[str]] = None,
                        limit: int = 50,
                        min_score: float = 0.01,
                        freshness_hours: Optional[int] = None) -> SearchResultSet:
        """
        Perform universal search across all indexed data domains
        
        Args:
            query: Search query text
            types: Optional list of document types to filter (forecast, news, brief, etc.)
            tickers: Optional list of tickers to filter
            sources: Optional list of sources to filter
            limit: Maximum number of results to return
            min_score: Minimum relevance score threshold
            freshness_hours: Optional hours filter for document freshness
        
        Returns:
            SearchResultSet with results and metadata
        """
        def compute_search_results():
            """Compute fresh search results from index"""
            try:
                # Convert string types to enum if needed
                type_enums = None
                if types:
                    type_enums = []
                    for t in types:
                        try:
                            if isinstance(t, str):
                                type_enums.append(SearchResultType(t.lower()))
                            else:
                                type_enums.append(t)
                        except ValueError:
                            # If invalid enum value, skip it
                            print(f"Warning: Invalid search result type: {t}")
                            continue
                
                # Calculate time cutoff if freshness filter specified
                time_cutoff = None
                if freshness_hours:
                    cutoff_time = datetime.utcnow() - timedelta(hours=freshness_hours)
                    time_cutoff = cutoff_time.isoformat() + "Z"
                
                # Perform search using the index
                search_results = self.search_index.search(
                    query=query,
                    types=type_enums,
                    tickers=tickers,
                    sources=sources,
                    limit=limit,
                    min_score=min_score
                )
                
                # Apply freshness filter after search if needed
                if time_cutoff:
                    filtered_results = []
                    for result in search_results.results:
                        if result.timestamp and result.timestamp >= time_cutoff:
                            filtered_results.append(result)
                    search_results.results = filtered_results
                    search_results.total_count = len(filtered_results)
                
                return search_results.to_dict()
                
            except Exception as e:
                print(f"Error in universal search computation: {str(e)}")
                
                # Fallback to return structured response to maintain never-empty contract
                return {
                    "results": [],
                    "query": query,
                    "total_count": 0,
                    "took_ms": 0,
                    "took_seconds": 0.0,
                    "filters_applied": {
                        "types": types,
                        "tickers": tickers,
                        "sources": sources,
                        "limit": limit,
                        "min_score": min_score,
                        "freshness_hours": freshness_hours
                    },
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "source": ["universal_search_service", "error_fallback", "fc-api-035"],
                    "error": str(e),
                    "message": "Search computation failed but fallback results generated to maintain never-empty contract"
                }
        
        # Use cache layer to serve latest available results, compute fresh if none available
        cache_key = f"universal_search_{hash(query + str(types) + str(tickers) + str(sources))}_{limit}"
        search_results = load_or_compute(
            key=cache_key,
            compute_fn=compute_search_results,
            source=["universal_search_service", "multi_domain_search", "fc-api-035"]
        )
        
        # Ensure proper response format
        if not isinstance(search_results, dict):
            search_results = {
                "results": [],
                "query": query,
                "total_count": 0,
                "took_ms": 0,
                "took_seconds": 0.0,
                "filters_applied": {
                    "types": types,
                    "tickers": tickers,
                    "sources": sources,
                    "limit": limit,
                    "min_score": min_score,
                    "freshness_hours": freshness_hours
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["universal_search_service", "format_fallback", "fc-api-035"],
                "message": "Invalid format returned from search, using fallback to maintain never-empty contract"
            }
        
        return search_results
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """
        Get search suggestions based on partial query
        
        Args:
            partial_query: Partial search query text
            
        Returns:
            List of suggested completions
        """
        try:
            # This would typically analyze the index to find related terms
            # For now, return a simple implementation based on common prefixes
            suggestions = []
            
            if not partial_query:
                # Return popular search terms
                return ["NVDA", "Apple", "Microsoft", "Fed", "CPI", "GDP", "FOMC"]
            
            # Look for documents that contain terms starting with the partial query
            for doc_id, doc in self.search_index.documents.items():
                content = doc.get("content", "")
                tokens = content.split()
                
                for token in tokens:
                    if token.startswith(partial_query.lower()) and len(token) > len(partial_query):
                        suggestion = token.title()  # Capitalize appropriately
                        if suggestion not in suggestions and len(suggestions) < 5:
                            suggestions.append(suggestion)
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            print(f"Error generating search suggestions: {str(e)}")
            return ["NVDA", "Apple", "Microsoft", "Fed", "CPI"]  # Fallback suggestions


# Global instance
universal_search_service = UniversalSearchService()


# Convenience functions
def universal_search(query: str,
                   types: Optional[List[str]] = None,
                   tickers: Optional[List[str]] = None,
                   sources: Optional[List[str]] = None,
                   limit: int = 50,
                   min_score: float = 0.01,
                   freshness_hours: Optional[int] = None):
    """
    Perform universal search across all domains
    """
    return universal_search_service.universal_search(query, types, tickers, sources, limit, min_score, freshness_hours)


def get_search_suggestions(partial_query: str):
    """
    Get search suggestions for autocomplete
    """
    return universal_search_service.get_search_suggestions(partial_query)