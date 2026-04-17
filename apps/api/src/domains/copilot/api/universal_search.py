"""
Universal Search API Routes - FC-API-035
Task: FC-API-035 - Endpoint /api/search/universal pour recherche globale (stocks, news, briefs, prévisions)
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime
from core.response import ok, err
from storage.io import load_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search")

try:
    from services.service_standard import ensure_decision_contract, utc_now_iso  # type: ignore
except Exception:  # pragma: no cover
    ensure_decision_contract = None  # type: ignore
    utc_now_iso = lambda: datetime.utcnow().isoformat() + "Z"  # type: ignore

def calculate_similarity(query: str, target: str) -> float:
    """
    Calculate similarity between query and target string using a simple algorithm
    Returns a score between 0 and 1 (1 being exact match)
    """
    query_lower = query.lower()
    target_lower = target.lower()
    
    if query_lower == target_lower:
        return 1.0
    
    # Check for substring match
    if query_lower in target_lower:
        # Higher score for substring matches
        return 0.8
    
    # Simple word overlap check
    query_words = set(query_lower.split())
    target_words = set(target_lower.split())
    overlap = len(query_words.intersection(target_words))
    
    if len(query_words) == 0 or len(target_words) == 0:
        return 0.0
    
    # Jaccard similarity
    union = len(query_words.union(target_words))
    return overlap / union if union > 0 else 0.0

@router.get("/universal")
async def universal_search_endpoint(
    q: str = Query(..., description="Search query string", min_length=1),
    type: Optional[str] = Query(None, description="Type of search (stocks, news, briefs, forecasts) or 'all'"),
    tickers: Optional[str] = Query(None, description="Restrict search to specific tickers (comma-separated)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results per category"),
    sort_by: str = Query('relevance', description="Sort order: relevance, date, score"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """
    Universal search endpoint for stocks, news, briefs, and forecasts
    """
    start_time = time.time()
    now_iso = utc_now_iso()
    
    # Normalize search types
    search_types = ['stocks', 'news', 'briefs', 'forecasts']
    if type and type.lower() != 'all':
        search_types = [t.strip().lower() for t in type.split(',') if t.strip()]
    
    # Parse ticker filter
    ticker_list = [t.strip().upper() for t in tickers.split(',')] if tickers else []
    
    results = {}
    total_results = 0
    
    try:
        # Search stocks
        if 'stocks' in search_types:
            stocks_data = load_json('stocks_universe') or []
            filtered_stocks = []
            
            for stock in stocks_data:
                ticker = str(stock.get('ticker', ''))
                name = str(stock.get('name', ''))
                
                # Filter by tickers if specified
                if ticker_list and ticker.upper() not in ticker_list:
                    continue
                
                # Calculate relevance score
                ticker_relevance = calculate_similarity(q, ticker)
                name_relevance = calculate_similarity(q, name)
                
                max_relevance = max(ticker_relevance, name_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1:
                    filtered_stocks.append({
                        **stock,
                        'relevance': max_relevance,
                        'match_field': 'ticker' if ticker_relevance > name_relevance else 'name'
                    })
            
            # Sort by relevance if requested
            if sort_by == 'relevance':
                filtered_stocks.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            # Sort by score if available
            elif sort_by == 'score':
                filtered_stocks.sort(key=lambda x: x.get('score', 0) or x.get('composite_score', 0), reverse=True)
            
            results['stocks'] = filtered_stocks[:limit]
            total_results += len(results['stocks'])
        
        # Search news
        if 'news' in search_types:
            news_data = load_json('news_feed') or {'articles': []}
            articles = news_data.get('articles', [])
            
            # Check if articles is nested in data (common pattern)
            if not articles and 'data' in news_data:
                nested_data = news_data['data']
                if isinstance(nested_data, list):
                    articles = nested_data
                elif isinstance(nested_data, dict) and 'articles' in nested_data:
                    articles = nested_data['articles']
            
            filtered_news = []
            for article in articles:
                title = str(article.get('title', ''))
                content = str(article.get('summary', '') or article.get('description', '') or '')
                tickers_in_article = article.get('tickers', []) or []
                
                # Filter by tickers if specified
                if ticker_list and not any(ticker.upper() in [t.upper() for t in tickers_in_article] for ticker in ticker_list):
                    continue
                
                # Calculate relevance score
                title_relevance = calculate_similarity(q, title)
                content_relevance = calculate_similarity(q, content)
                ticker_tag_relevance = calculate_similarity(q, ' '.join(map(str, tickers_in_article))) if tickers_in_article else 0
                
                max_relevance = max(title_relevance, content_relevance, ticker_tag_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1 or q.lower() in [t.lower() for t in tickers_in_article]:
                    filtered_news.append({
                        **article,
                        'relevance': max_relevance,
                        'match_field': 'title' if title_relevance >= content_relevance else 'content'
                    })
            
            # Sort by relevance or date if requested
            if sort_by == 'relevance':
                filtered_news.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            elif sort_by == 'date':
                filtered_news.sort(key=lambda x: x.get('pub_date') or x.get('date') or '1970-01-01', reverse=True)
            
            results['news'] = filtered_news[:limit]
            total_results += len(results['news'])
        
        # Search briefs
        if 'briefs' in search_types:
            briefs_data = load_json('brief_weekly') or {}
            
            # Structure might vary - look for different formats
            brief_items = []
            if 'data' in briefs_data:
                brief_data = briefs_data['data']
                if isinstance(brief_data, list):
                    brief_items = brief_data
                elif isinstance(brief_data, dict):
                    # Common single-object format, might include top_signals, top_risks, etc.
                    for key in ['top_signals', 'top_risks', 'picks', 'highlights', 'signals', 'risks']:
                        if key in brief_data and isinstance(brief_data[key], list):
                            brief_items.extend(brief_data[key])
            # Check if briefs_data itself is an array of items
            elif isinstance(briefs_data, list):
                brief_items = briefs_data
            
            filtered_briefs = []
            for item in brief_items:
                title = str(item.get('title', '') or item.get('ticker', '') or '')
                content = str(item.get('summary', '') or item.get('description', '') or str(item.get('reason', '')) or '')
                
                # Calculate relevance score
                title_relevance = calculate_similarity(q, title)
                content_relevance = calculate_similarity(q, content)
                
                max_relevance = max(title_relevance, content_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1:
                    filtered_briefs.append({
                        **item,
                        'relevance': max_relevance,
                        'item_type': item.get('type', 'brief')
                    })
            
            if sort_by == 'relevance':
                filtered_briefs.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            elif sort_by == 'date':
                filtered_briefs.sort(key=lambda x: x.get('generated_at') or x.get('date') or '1970-01-01', reverse=True)
            
            results['briefs'] = filtered_briefs[:limit]
            total_results += len(results['briefs'])
        
        # Search forecasts
        if 'forecasts' in search_types:
            forecasts_data = load_json('forecasts') or {'rows': []}
            forecast_items = forecasts_data.get('rows', [])
            
            # Check alternative structures
            if not forecast_items and 'data' in forecasts_data:
                data = forecasts_data['data']
                if isinstance(data, list):
                    forecast_items = data
                elif isinstance(data, dict) and 'rows' in data:
                    forecast_items = data['rows']
            
            filtered_forecasts = []
            for forecast in forecast_items:
                ticker = str(forecast.get('ticker', '') or forecast.get('symbol', ''))
                horizon = str(forecast.get('horizon', ''))
                explanation = str(forecast.get('explanation', '') or forecast.get('reason', '') or '')
                
                # Filter by tickers if specified
                if ticker_list and ticker.upper() not in ticker_list:
                    continue
                
                # Calculate relevance score
                ticker_relevance = calculate_similarity(q, ticker)
                horizon_relevance = calculate_similarity(q, horizon)
                explanation_relevance = calculate_similarity(q, explanation)
                
                max_relevance = max(ticker_relevance, horizon_relevance, explanation_relevance)
                
                # Only include if relevance score is above threshold
                if max_relevance > 0.1:
                    filtered_forecasts.append({
                        **forecast,
                        'relevance': max_relevance,
                        'match_field': 'ticker' if ticker_relevance >= max(horizon_relevance, explanation_relevance) else
                                     'horizon' if horizon_relevance >= explanation_relevance else 'explanation'
                    })
            
            if sort_by == 'relevance':
                filtered_forecasts.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            elif sort_by == 'score':
                filtered_forecasts.sort(key=lambda x: x.get('score') or x.get('confidence', 0), reverse=True)
            
            results['forecasts'] = filtered_forecasts[:limit]
            total_results += len(results['forecasts'])
        
        # Calculate execution time
        exec_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Universal search completed: {total_results} results in {exec_time_ms}ms")
        
        # Prepare response
        response_data = {
            'query': q,
            'results': results,
            'total': total_results,
            'execution_time': exec_time_ms,
            'generated_at': now_iso,
            'freshness': now_iso,
            'source': ['universal_search'],
            'search_metadata': {
                'types_searched': search_types,
                'tickers_filtered': ticker_list if ticker_list else None,
                'date_range': {
                    'from': date_from,
                    'to': date_to
                } if date_from or date_to else None,
                'sort_by': sort_by
            }
        }

        if callable(ensure_decision_contract):
            ensure_decision_contract(
                response_data,
                default_source="universal_search",
                verdict="hold",
                confidence=0.0,
                why=["Universal search payload (no trading action)."],
                risk_level="low",
                freshness=now_iso,
            )
        
        return ok(response_data)
        
    except Exception as e:
        logger.error(f"Error in universal search: {str(e)}", exc_info=True)
        return err(f"Universal search failed: {str(e)}", code=500)


universal_search_router = router

# Export the router for use in main API app
search_router = router
