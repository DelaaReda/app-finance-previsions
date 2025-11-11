"""
Market Embedding with Node2Vec approach
Part of the Finance Copilot forecasting engine
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
import networkx as nx
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

try:
    from node2vec import Node2Vec
    NODE2VEC_AVAILABLE = True
except ImportError:
    NODE2VEC_AVAILABLE = False


class MarketEmbedding:
    """
    Market embedding using Node2Vec approach to capture relationships
    between different market entities and their movements
    """
    
    def __init__(self, dimensions: int = 50, walk_length: int = 30, num_walks: int = 200):
        self.dimensions = dimensions
        self.walk_length = walk_length
        self.num_walks = num_walks
        self.graph = None
        self.model = None
        self.embeddings = None
        self.scaler = StandardScaler()
        
    def _build_correlation_graph(self, data: pd.DataFrame, threshold: float = 0.1) -> nx.Graph:
        """
        Build a correlation graph from market data
        
        Args:
            data: Market data with multiple assets
            threshold: Minimum correlation to create edge
            
        Returns:
            NetworkX Graph
        """
        # Calculate correlation matrix
        corr_matrix = data.select_dtypes(include=[np.number]).corr()
        
        # Create graph
        G = nx.Graph()
        
        # Add nodes (assets)
        for asset in corr_matrix.columns:
            G.add_node(asset)
        
        # Add edges based on correlation
        for i, asset1 in enumerate(corr_matrix.columns):
            for j, asset2 in enumerate(corr_matrix.columns):
                if i != j and abs(corr_matrix.iloc[i, j]) > threshold:
                    G.add_edge(asset1, asset2, weight=corr_matrix.iloc[i, j])
        
        return G
    
    def _build_cointegration_graph(self, data: pd.DataFrame, significance_level: float = 0.05) -> nx.Graph:
        """
        Build a cointegration graph from market data (simplified approach)
        
        Args:
            data: Market data with multiple assets
            significance_level: P-value threshold for cointegration
            
        Returns:
            NetworkX Graph
        """
        # For this implementation, we'll use a simplified approach
        # In a full implementation, we'd perform actual cointegration tests
        G = nx.Graph()
        
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for asset in numeric_cols:
            G.add_node(asset)
        
        # Add edges based on mutual information or correlation (simplified)
        corr_matrix = data[numeric_cols].corr()
        
        for i, asset1 in enumerate(corr_matrix.columns):
            for j, asset2 in enumerate(corr_matrix.columns):
                if i != j and abs(corr_matrix.iloc[i, j]) > 0.3:  # Higher threshold for cointegration
                    G.add_edge(asset1, asset2, weight=corr_matrix.iloc[i, j])
        
        return G
    
    def _build_temporal_graph(self, data: pd.DataFrame, time_window: int = 5) -> nx.Graph:
        """
        Build a temporal graph based on price movements patterns
        
        Args:
            data: Time series data
            time_window: Window size for pattern matching
            
        Returns:
            NetworkX Graph
        """
        G = nx.Graph()
        
        if 'close' in data.columns:
            # Create temporal pattern nodes
            returns = data['close'].pct_change().dropna()
            
            # Create pattern sequences
            for i in range(len(returns) - time_window):
                pattern = tuple(returns.iloc[i:i+time_window])
                pattern_name = f"pattern_{i}"
                G.add_node(pattern_name, pattern=pattern)
                
                # Connect to next pattern
                if i > 0:
                    prev_pattern_name = f"pattern_{i-1}"
                    G.add_edge(prev_pattern_name, pattern_name)
        
        return G
    
    def fit(self, data: pd.DataFrame, method: str = 'correlation') -> 'MarketEmbedding':
        """
        Fit the market embedding model
        
        Args:
            data: Market data with multiple assets or features
            method: Method to build graph ('correlation', 'cointegration', 'temporal')
            
        Returns:
            Self
        """
        if method == 'correlation':
            self.graph = self._build_correlation_graph(data)
        elif method == 'cointegration':
            self.graph = self._build_cointegration_graph(data)
        elif method == 'temporal':
            self.graph = self._build_temporal_graph(data)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        if NODE2VEC_AVAILABLE and self.graph and len(self.graph.nodes()) > 1:
            # Create node2vec model
            node2vec = Node2Vec(
                self.graph,
                dimensions=self.dimensions,
                walk_length=self.walk_length,
                num_walks=self.num_walks,
                workers=1
            )
            
            # Fit the model
            self.model = node2vec.fit(window=10, min_count=1)
            
            # Get embeddings
            self.embeddings = {}
            for node in self.graph.nodes():
                try:
                    self.embeddings[node] = self.model.wv[node]
                except KeyError:
                    # Node not in model, assign random embedding
                    self.embeddings[node] = np.random.rand(self.dimensions)
        else:
            # Fallback: create simple embeddings based on statistical features
            self._create_statistical_embeddings(data)
        
        return self
    
    def _create_statistical_embeddings(self, data: pd.DataFrame) -> None:
        """
        Create embeddings based on statistical features if Node2Vec is not available
        """
        # Select numeric columns
        numeric_data = data.select_dtypes(include=[np.number])
        
        # Calculate statistical features for each column
        features = {}
        for col in numeric_data.columns:
            series = numeric_data[col].dropna()
            if len(series) > 1:
                features[col] = [
                    series.mean(),
                    series.std(),
                    series.skew(),
                    series.kurtosis(),
                    series.min(),
                    series.max(),
                    series.quantile(0.25),
                    series.quantile(0.75)
                ]
        
        # Standardize features
        feature_matrix = np.array(list(features.values()))
        feature_matrix = self.scaler.fit_transform(feature_matrix)
        
        # Create embeddings
        self.embeddings = {}
        for i, col in enumerate(features.keys()):
            # Use PCA to reduce to desired dimensions
            if feature_matrix.shape[1] >= self.dimensions:
                pca = PCA(n_components=self.dimensions)
                reduced_features = pca.fit_transform(feature_matrix)
                self.embeddings[col] = reduced_features[i]
            else:
                # Pad with zeros if needed
                emb = np.zeros(self.dimensions)
                emb[:len(features[col])] = features[col]
                self.embeddings[col] = emb
    
    def get_embedding(self, node: str) -> np.ndarray:
        """
        Get embedding for a specific node
        
        Args:
            node: Node name
            
        Returns:
            Embedding vector
        """
        if self.embeddings and node in self.embeddings:
            return self.embeddings[node]
        else:
            # Return a random embedding if node not found
            return np.random.rand(self.dimensions)
    
    def get_all_embeddings(self) -> Dict[str, np.ndarray]:
        """
        Get all embeddings
        
        Returns:
            Dictionary of embeddings
        """
        return self.embeddings or {}
    
    def similarity(self, node1: str, node2: str) -> float:
        """
        Calculate similarity between two nodes using their embeddings
        
        Args:
            node1: First node name
            node2: Second node name
            
        Returns:
            Similarity score (cosine similarity)
        """
        emb1 = self.get_embedding(node1)
        emb2 = self.get_embedding(node2)
        
        # Calculate cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar_nodes(self, node: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find nodes similar to the given node
        
        Args:
            node: Reference node
            top_k: Number of similar nodes to return
            
        Returns:
            List of (node_name, similarity_score) tuples
        """
        if not self.embeddings:
            return []
        
        similarities = []
        for other_node in self.embeddings.keys():
            if other_node != node:
                sim = self.similarity(node, other_node)
                similarities.append((other_node, sim))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


def create_market_embedding(**kwargs) -> MarketEmbedding:
    """
    Factory function to create a market embedding model
    """
    return MarketEmbedding(**kwargs)


def example_usage():
    """
    Example of how to use the MarketEmbedding class
    """
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='D')
    
    # Create correlated data
    spy_returns = np.random.normal(0.0005, 0.02, 252)
    qqq_returns = spy_returns + np.random.normal(0, 0.01, 252)
    tlt_returns = np.random.normal(-0.0002, 0.015, 252)  # Inverse correlation example
    
    # Convert to prices
    spy_prices = [100]
    qqq_prices = [200]
    tlt_prices = [90]
    
    for i in range(1, 252):
        spy_prices.append(spy_prices[-1] * (1 + spy_returns[i]))
        qqq_prices.append(qqq_prices[-1] * (1 + qqq_returns[i]))
        tlt_prices.append(tlt_prices[-1] * (1 + tlt_returns[i]))
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'spy_close': spy_prices,
        'qqq_close': qqq_prices,
        'tlt_close': tlt_prices,
        'spy_volume': np.random.randint(50000000, 100000000, 252),
        'qqq_volume': np.random.randint(30000000, 60000000, 252),
        'tlt_volume': np.random.randint(10000000, 25000000, 252)
    })
    
    # Create market embedding
    market_emb = MarketEmbedding(dimensions=10, walk_length=20, num_walks=10)
    
    # Fit the model using correlation method
    market_emb.fit(df, method='correlation')
    
    # Get embeddings
    all_embeddings = market_emb.get_all_embeddings()
    print(f"Number of embeddings created: {len(all_embeddings)}")
    
    # Test similarity
    if 'spy_close' in all_embeddings and 'qqq_close' in all_embeddings:
        similarity = market_emb.similarity('spy_close', 'qqq_close')
        print(f"Similarity between spy_close and qqq_close: {similarity:.4f}")
    
    # Find similar nodes
    similar_nodes = market_emb.find_similar_nodes('spy_close', top_k=3)
    print(f"Top 3 similar nodes to spy_close: {similar_nodes}")
    
    return market_emb, df


if __name__ == "__main__":
    print("MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7: Testing Market Embedding...")
    market_emb, df = example_usage()