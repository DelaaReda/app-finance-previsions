"""
Search Result Model
Task: FC-API-035 - Universal Search
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class SearchResultType(str, Enum):
    """
    Types of search results supported by universal search
    """
    STOCK = "stock"
    NEWS = "news"
    FORECAST = "forecast"
    BRIEF = "brief"
    MACRO = "macro"
    ARTICLE = "article"
    REPORT = "report"


@dataclass
class SearchResult:
    """
    Model representing a single search result
    """
    id: str
    title: str
    content: str
    type: SearchResultType
    source: str
    score: float  # Relevance score 0.0-1.0 (higher is more relevant)
    timestamp: str
    ticker: Optional[str] = None  # Associated ticker if any
    url: Optional[str] = None  # Link to the resource
    summary: Optional[str] = None  # Short summary/description
    tags: Optional[List[str]] = None  # Associated tags/keywords
    freshness_minutes: Optional[int] = None  # Minutes since last update
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API response"""
        result = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type.value if isinstance(self.type, SearchResultType) else self.type,
            "source": self.source,
            "score": self.score,
            "timestamp": self.timestamp,
            "ticker": self.ticker,
            "url": self.url,
            "summary": self.summary,
            "tags": self.tags or [],
            "freshness_minutes": self.freshness_minutes
        }
        # Remove None values to keep the response clean
        return {k: v for k, v in result.items() if v is not None}


class SearchResultSet:
    """
    Container for search results with metadata
    """
    
    def __init__(self,
                 results: List[SearchResult],
                 query: str,
                 total_count: int,
                 took_ms: int,
                 took_seconds: float,
                 filters: Optional[Dict[str, Any]] = None):
        self.results = results
        self.query = query
        self.total_count = total_count
        self.took_ms = took_ms
        self.took_seconds = took_seconds
        self.filters = filters or {}
        self.generated_at = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API response"""
        return {
            "results": [result.to_dict() for result in self.results],
            "query": self.query,
            "total_count": self.total_count,
            "took_ms": self.took_ms,
            "took_seconds": self.took_seconds,
            "filters_applied": self.filters,
            "generated_at": self.generated_at,
            "source": ["universal_search_model", "search_result_aggregation", "fc-api-035"]
        }


class SearchIndex:
    """
    In-memory search index for fast full-text search
    In production, this would be replaced with Elasticsearch, PostgreSQL full-text search, etc.
    """
    
    def __init__(self):
        self.documents = {}  # Map of doc_id to document
        self.index = {}  # Word -> [doc_ids]
        self.type_index = {}  # type -> [doc_ids]
        self.ticker_index = {}  # ticker -> [doc_ids]
        self.source_index = {}  # source -> [doc_ids]
    
    def add_document(self, doc_id: str, content: str, doc_type: SearchResultType, 
                    ticker: Optional[str] = None, source: str = "unknown", **kwargs):
        """
        Add a document to the search index
        
        Args:
            doc_id: Unique identifier for the document
            content: Full text content of the document
            doc_type: Type of document (stock, news, forecast, etc.)
            ticker: Associated ticker symbol
            source: Source of the document
            **kwargs: Additional metadata fields
        """
        # Store document
        self.documents[doc_id] = {
            "id": doc_id,
            "content": content.lower(),  # Store lowercase for case-insensitive search
            "type": doc_type,
            "ticker": ticker.upper() if ticker else None,
            "source": source,
            **kwargs
        }
        
        # Add to type index
        doc_type_str = doc_type.value if isinstance(doc_type, SearchResultType) else str(doc_type)
        if doc_type_str not in self.type_index:
            self.type_index[doc_type_str] = []
        self.type_index[doc_type_str].append(doc_id)
        
        # Add to ticker index if ticker provided
        if ticker:
            ticker_upper = ticker.upper()
            if ticker_upper not in self.ticker_index:
                self.ticker_index[ticker_upper] = []
            self.ticker_index[ticker_upper].append(doc_id)
        
        # Add to source index
        if source not in self.source_index:
            self.source_index[source] = []
        self.source_index[source].append(doc_id)
        
        # Tokenize content and add to inverted index
        tokens = self._tokenize(content)
        for token in tokens:
            if token not in self.index:
                self.index[token] = []
            if doc_id not in self.index[token]:
                self.index[token].append(doc_id)
    
    def search(self, 
               query: str, 
               types: Optional[List[SearchResultType]] = None,
               tickers: Optional[List[str]] = None,
               sources: Optional[List[str]] = None,
               limit: int = 50,
               min_score: float = 0.01) -> List[Dict[str, Any]]:
        """
        Perform search across indexed documents
        
        Args:
            query: Search query text
            types: Optional list of document types to filter
            tickers: Optional list of tickers to filter
            sources: Optional list of sources to filter
            limit: Maximum number of results to return
            min_score: Minimum relevance score threshold
        
        Returns:
            List of search results with scoring
        """
        if not query or not query.strip():
            return []
        
        start_time = datetime.utcnow()
        
        # Tokenize query
        query_tokens = self._tokenize(query.lower())
        
        # Get candidate documents (those containing any query terms)
        candidate_doc_ids = set()
        query_term_counts = {}
        
        for token in query_tokens:
            if token in self.index:
                for doc_id in self.index[token]:
                    candidate_doc_ids.add(doc_id)
                    query_term_counts[doc_id] = query_term_counts.get(doc_id, 0) + 1
        
        # Apply filters
        filtered_doc_ids = []
        
        for doc_id in candidate_doc_ids:
            doc = self.documents.get(doc_id, {})
            
            # Type filter
            if types:
                doc_type = doc.get("type")
                doc_type_str = doc_type.value if isinstance(doc_type, SearchResultType) else str(doc_type)
                if doc_type_str not in [t.value if isinstance(t, SearchResultType) else str(t) for t in types]:
                    continue
            
            # Ticker filter
            if tickers:
                doc_ticker = doc.get("ticker")
                if doc_ticker and doc_ticker.upper() not in [t.upper() for t in tickers]:
                    continue
            
            # Source filter
            if sources:
                doc_source = doc.get("source")
                if doc_source and doc_source not in sources:
                    continue
            
            filtered_doc_ids.append(doc_id)
        
        # Calculate relevance scores
        results = []
        for doc_id in filtered_doc_ids:
            doc = self.documents[doc_id]
            doc_content = doc.get("content", "")
            doc_tokens = set(self._tokenize(doc_content))
            
            # Calculate TF-IDF like score
            # Simple version: ratio of matching terms to total query terms
            matching_terms = 0
            for token in query_tokens:
                if token in doc_tokens:
                    matching_terms += 1
            
            # Base score: proportion of query terms found in document
            base_score = matching_terms / len(query_tokens) if len(query_tokens) > 0 else 0.0
            
            # Boost score if document contains all query terms
            if matching_terms == len(query_tokens):
                base_score *= 1.5  # Perfect match bonus
            
            # Boost score if document type is specifically requested
            if types and doc.get("type") in types:
                base_score *= 1.2  # Type match bonus
            
            # Boost score if ticker is specifically requested
            if tickers and doc.get("ticker") and doc["ticker"].upper() in [t.upper() for t in tickers]:
                base_score *= 1.3  # Ticker match bonus
            
            # Only include if score meets minimum threshold
            if base_score >= min_score:
                # Create search result object
                result = {
                    "id": doc_id,
                    "title": doc.get("title", doc_id),  # Use ID as fallback for title
                    "content": doc_content[:500] + "..." if len(doc_content) > 500 else doc_content,  # Truncate long content
                    "type": doc.get("type"),
                    "source": doc.get("source", "unknown"),
                    "score": base_score,
                    "timestamp": doc.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                    "ticker": doc.get("ticker"),
                    "url": doc.get("url"),
                    "summary": doc.get("summary") or (doc_content[:100] + "..." if len(doc_content) > 100 else doc_content),
                    "tags": doc.get("tags", []),
                    "freshness_minutes": self._calculate_freshness_minutes(doc.get("timestamp"))
                }
                
                results.append(result)
        
        # Sort by score (descending) then by freshness (newest first)
        results.sort(key=lambda x: (x["score"], -x.get("freshness_minutes", float('inf')) or float('inf')), reverse=True)
        
        # Limit results
        results = results[:limit]
        
        # Calculate time taken
        end_time = datetime.utcnow()
        took_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Create search result set
        result_set = SearchResultSet(
            results=[self._dict_to_search_result(r) for r in results],
            query=query,
            total_count=len(results),
            took_ms=took_ms,
            took_seconds=(end_time - start_time).total_seconds(),
            filters={
                "types": [t.value if isinstance(t, SearchResultType) else str(t) for t in types] if types else None,
                "tickers": [t.upper() for t in tickers] if tickers else None,
                "sources": sources,
                "limit": limit,
                "min_score": min_score
            }
        )
        
        return result_set
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenizer to split text into tokens
        """
        import re
        # Remove punctuation and split on whitespace
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Filter out very short tokens
        return [token for token in tokens if len(token) > 2]
    
    def _calculate_freshness_minutes(self, timestamp_str: Optional[str]) -> Optional[int]:
        """
        Calculate how many minutes ago a document was created/updated
        """
        if not timestamp_str:
            return None
        
        try:
            from datetime import timezone
            import re
            
            # Handle different timestamp formats
            if 'Z' in timestamp_str:
                # UTC format with Z
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif timestamp_str.endswith('+00:00'):
                # UTC format with +00:00
                dt = datetime.fromisoformat(timestamp_str)
            else:
                # Try to parse other formats
                dt = datetime.fromisoformat(timestamp_str)
            
            # Convert to UTC if it's offset-aware
            if dt.tzinfo is None:
                # Assume UTC if no timezone info
                import pytz
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            now = datetime.now(timezone.utc)
            diff = now - dt
            return int(diff.total_seconds() // 60)
        except:
            return None  # Return None if parsing fails
    
    def _dict_to_search_result(self, result_dict: Dict[str, Any]) -> SearchResult:
        """
        Convert dictionary result to SearchResult object
        """
        return SearchResult(
            id=result_dict["id"],
            title=result_dict["title"],
            content=result_dict["content"],
            type=SearchResultType(result_dict["type"]) if isinstance(result_dict["type"], str) else result_dict["type"],
            source=result_dict["source"],
            score=result_dict["score"],
            timestamp=result_dict["timestamp"],
            ticker=result_dict.get("ticker"),
            url=result_dict.get("url"),
            summary=result_dict.get("summary"),
            tags=result_dict.get("tags"),
            freshness_minutes=result_dict.get("freshness_minutes")
        )


# Global search index instance
universal_search_index = SearchIndex()


def create_search_result(id: str, title: str, content: str, type: SearchResultType, 
                        source: str, score: float, timestamp: str,
                        ticker: Optional[str] = None, url: Optional[str] = None,
                        summary: Optional[str] = None, tags: Optional[List[str]] = None) -> SearchResult:
    """
    Create a search result instance
    """
    return SearchResult(id, title, content, type, source, score, timestamp, ticker, url, summary, tags)