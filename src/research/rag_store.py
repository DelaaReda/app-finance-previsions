"""
RAG Store - Mémoire pour le Copilot
Stocke et indexe les news + facts séries pour Q&A avec citations.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib


class RAGStore:
    """Store minimal pour RAG avec news et facts séries."""
    
    def __init__(self, storage_dir: str = "data/rag"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.news_file = self.storage_dir / "news.jsonl"
        self.facts_file = self.storage_dir / "facts.jsonl"
        
        # Créer fichiers si inexistants
        self.news_file.touch(exist_ok=True)
        self.facts_file.touch(exist_ok=True)
    
    def _generate_id(self, text: str) -> str:
        """Génère un ID unique pour un texte."""
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    def add_news_item(self, item: Dict[str, Any]) -> None:
        """
        Ajoute un item de news à la mémoire.
        
        Args:
            item: Dict avec {title, url, published, summary, score, etc.}
        """
        # Créer chunk avec métadonnées
        chunk = {
            "id": self._generate_id(item.get("title", "") + item.get("url", "")),
            "text": f"{item.get('title', '')}. {item.get('summary', '')}",
            "meta": {
                "type": "news",
                "url": item.get("url", ""),
                "date": item.get("published", ""),
                "ticker": item.get("tickers", [])[0] if item.get("tickers") else "",
                "score": item.get("score", 0),
                "source": item.get("source", "")
            },
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        # Append au fichier JSONL
        with open(self.news_file, "a") as f:
            f.write(json.dumps(chunk) + "\n")
    
    def add_news_items(self, items: List[Dict[str, Any]]) -> None:
        """Ajoute plusieurs items de news."""
        for item in items:
            self.add_news_item(item)
    
    def add_series_fact(self, series_id: str, name: str, value: float, date: str) -> None:
        """
        Ajoute un fact de série macro/prix.
        
        Args:
            series_id: ID série (ex: "CPIAUCSL", "AAPL")
            name: Nom lisible (ex: "CPI", "Apple Stock")
            value: Valeur
            date: Date (ISO format)
        """
        # Créer fact lisible
        text = f"{name} était à {value:.2f} le {date}"
        
        chunk = {
            "id": self._generate_id(f"{series_id}_{date}"),
            "text": text,
            "meta": {
                "type": "series",
                "series_id": series_id,
                "name": name,
                "value": value,
                "date": date,
                "url": f"https://fred.stlouisfed.org/series/{series_id}" if len(series_id) > 3 else ""
            },
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        with open(self.facts_file, "a") as f:
            f.write(json.dumps(chunk) + "\n")
    
    def add_series_facts(self, series_dict: Dict[str, Any]) -> None:
        """
        Ajoute plusieurs facts de séries.
        
        Args:
            series_dict: {series_id: {name, values: [{date, value}]}}
        """
        for series_id, data in series_dict.items():
            name = data.get("name", series_id)
            values = data.get("values", [])
            for val in values[-10:]:  # Dernières 10 valeurs
                self.add_series_fact(series_id, name, val["value"], val["date"])
    
    def search(self, scope: Optional[Dict[str, Any]] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche dans la mémoire RAG.
        
        Args:
            scope: Filtres optionnels {tickers: [...], horizon: "1w"}
            top_k: Nombre max de résultats
        
        Returns:
            Liste de chunks avec métadonnées
        """
        results = []
        
        # Extraire filtres
        tickers = scope.get("tickers", []) if scope else []
        
        # Lire news
        try:
            with open(self.news_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    
                    # Filtrer par ticker si spécifié
                    if tickers:
                        chunk_ticker = chunk["meta"].get("ticker", "")
                        if chunk_ticker not in tickers:
                            continue
                    
                    results.append(chunk)
        except Exception as e:
            print(f"Erreur lecture news: {e}")
        
        # Lire facts séries
        try:
            with open(self.facts_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    results.append(chunk)
        except Exception as e:
            print(f"Erreur lecture facts: {e}")
        
        # Trier par score/date (news en priorité)
        results.sort(key=lambda x: (
            x["meta"].get("score", 0) if x["meta"]["type"] == "news" else 0.5,
            x["meta"].get("date", "")
        ), reverse=True)
        
        return results[:top_k]
    
    def clear(self) -> None:
        """Vide la mémoire RAG."""
        self.news_file.unlink(missing_ok=True)
        self.facts_file.unlink(missing_ok=True)
        self.news_file.touch()
        self.facts_file.touch()
    
    def stats(self) -> Dict[str, int]:
        """Retourne statistiques de la mémoire."""
        news_count = 0
        facts_count = 0
        
        try:
            with open(self.news_file, "r") as f:
                news_count = sum(1 for line in f if line.strip())
        except:
            pass
        
        try:
            with open(self.facts_file, "r") as f:
                facts_count = sum(1 for line in f if line.strip())
        except:
            pass
        
        return {
            "news_count": news_count,
            "facts_count": facts_count,
            "total": news_count + facts_count
        }
