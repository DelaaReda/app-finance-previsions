# TÂCHES PRIORITAIRES POUR AGENTS - Sprint Post-P0

**Créé par** : CLAUDE-STABILITY-ARCHITECT-IRONMAN-42
**Date** : 2025-11-04
**Source** : Analyses FC-VISION-001 et FC-VISION-002
**Statut P0** : ✅ COMPLÉTÉ (+390 pts) - Scheduler + Startup Init + Cache Verification

---

## 🎯 CONTEXTE

Suite à mes analyses approfondies (FC-VISION-001 & FC-VISION-002) et à l'implémentation des tâches P0, voici les **tâches prioritaires suivantes** pour améliorer la qualité, performance et fiabilité du Finance Copilot.

Toutes les tâches incluent :
- ✅ Spécifications détaillées
- ✅ How-to step-by-step
- ✅ Critères d'acceptance
- ✅ Points estimés selon le barème AGENTS.md

---

## 📋 TÂCHES PRIORITÉ 1 (P1) - 1,000+ points disponibles

---

### 🔥 FC-IMPORTS-CLEANUP-001 : Corriger imports cassés (+50 pts)

**Agent recommandé** : Tout agent disponible
**Urgence** : 🔴 CRITIQUE (bloque tests end-to-end)
**Durée estimée** : 30 minutes
**Dépendances** : Aucune

#### Problème

7 fichiers ont des imports cassés `from backend.storage.*` qui empêchent le démarrage de l'application. 2 fichiers déjà corrigés, reste 5.

#### Fichiers à corriger

```
✅ copilot-app/backend/services/cache_layer.py (FAIT)
✅ copilot-app/backend/src/api/main.py (FAIT)
❌ copilot-app/backend/jobs/forecasts.py
❌ copilot-app/backend/src/api/services/forecast_service.py
❌ copilot-app/backend/src/ingestion/finnews_fixed.py
❌ copilot-app/backend/models/forecast_v0/enhanced_metrics.py
❌ copilot-app/backend/src/research/alerts.py
```

#### How-to

**Étape 1** : Trouver tous les imports cassés
```bash
cd /Users/venom/Documents/analyse-financiere/copilot-app/backend
grep -n "from backend.storage" jobs/forecasts.py
grep -n "from backend.storage" src/api/services/forecast_service.py
grep -n "from backend.storage" src/ingestion/finnews_fixed.py
grep -n "from backend.storage" models/forecast_v0/enhanced_metrics.py
grep -n "from backend.storage" src/research/alerts.py
```

**Étape 2** : Pour chaque fichier, remplacer les imports

```python
# AVANT (cassé)
from backend.storage.base import load_json, save_json
from backend.storage.io import load_json, save_json

# APRÈS (correct)
from storage.base import load_json, save_json
from storage.io import load_json, save_json
```

**Étape 3** : Ajouter APScheduler au requirements.txt
```bash
echo "apscheduler>=3.10.0" >> requirements.txt
```

**Étape 4** : Tester
```bash
.venv/bin/python3 run_api.py
# Vérifier qu'il n'y a plus d'erreurs "ModuleNotFoundError: No module named 'backend.storage'"
```

#### Critères d'acceptance

- [ ] Les 5 fichiers ont leurs imports corrigés
- [ ] APScheduler ajouté au requirements.txt
- [ ] L'application démarre sans erreur d'import
- [ ] Logs montrent "✅ Finance Copilot Ready!"

#### Preuve requise

- Screenshot des logs de démarrage réussi
- Sortie de `grep "from backend.storage" **/*.py` (doit être vide)

---

### 📊 FC-TTL-001 : Système de TTL pour cache (+100 pts)

**Agent recommandé** : ALEX-BACKEND-SUPERMAN-7 ou STEPHANE-DATA-MASTER-BATMAN-10
**Urgence** : 🟡 ÉLEVÉE
**Durée estimée** : 2 heures
**Dépendances** : FC-IMPORTS-CLEANUP-001

#### Problème

Actuellement, aucun système de TTL (Time-To-Live). Les données peuvent être stale sans détection. Besoin de :
- TTL configurable par type de données
- Détection automatique des données expirées
- Metadata `is_fresh` dans les réponses API

#### Spécifications

**TTL par type de données** :
```python
TTL_CONFIG = {
    "forecasts": 24 * 3600,        # 24h (refresh quotidien)
    "news_feed": 15 * 60,          # 15 min (refresh fréquent)
    "brief_weekly": 7 * 24 * 3600, # 7 jours
    "brief_daily": 24 * 3600,      # 24h
    "alerts": 30 * 60,             # 30 min
    "backtests": 30 * 24 * 3600,   # 30 jours
}
```

#### How-to

**Étape 1** : Créer le module TTL

Fichier : `copilot-app/backend/storage/ttl.py`

```python
"""
TTL (Time-To-Live) system for cached data
Task: FC-TTL-001 (+100 pts)
Author: <VOTRE-HANDLE>
"""
from datetime import datetime, timedelta
from typing import Dict, Optional

# TTL configuration (in seconds)
TTL_CONFIG = {
    "forecasts": 24 * 3600,        # 24h
    "news_feed": 15 * 60,          # 15 min
    "brief_weekly": 7 * 24 * 3600, # 7 days
    "brief_daily": 24 * 3600,      # 24h
    "alerts": 30 * 60,             # 30 min
    "backtests": 30 * 24 * 3600,   # 30 days
}

def is_fresh(data: Dict, data_type: str) -> bool:
    """
    Check if cached data is still fresh based on TTL

    Args:
        data: The cached data dictionary
        data_type: Type of data (e.g., "forecasts", "news_feed")

    Returns:
        True if data is fresh, False if stale or missing freshness info
    """
    if not data or "freshness" not in data:
        return False

    ttl_seconds = TTL_CONFIG.get(data_type)
    if ttl_seconds is None:
        # Unknown data type, assume stale
        return False

    try:
        # Parse ISO timestamp
        freshness_str = data["freshness"]
        if freshness_str.endswith("Z"):
            freshness_str = freshness_str[:-1] + "+00:00"

        freshness_time = datetime.fromisoformat(freshness_str)
        now = datetime.now(freshness_time.tzinfo)
        age_seconds = (now - freshness_time).total_seconds()

        return age_seconds < ttl_seconds

    except Exception as e:
        print(f"⚠️  Error parsing freshness timestamp: {e}")
        return False

def get_freshness_metadata(data: Dict, data_type: str) -> Dict:
    """
    Get metadata about data freshness

    Returns:
        {
            "is_fresh": bool,
            "age_seconds": float,
            "ttl_seconds": int,
            "expires_at": str (ISO),
            "status": "fresh" | "stale" | "unknown"
        }
    """
    if not data or "freshness" not in data:
        return {
            "is_fresh": False,
            "age_seconds": None,
            "ttl_seconds": TTL_CONFIG.get(data_type),
            "expires_at": None,
            "status": "unknown"
        }

    ttl_seconds = TTL_CONFIG.get(data_type)

    try:
        freshness_str = data["freshness"]
        if freshness_str.endswith("Z"):
            freshness_str = freshness_str[:-1] + "+00:00"

        freshness_time = datetime.fromisoformat(freshness_str)
        now = datetime.now(freshness_time.tzinfo)
        age_seconds = (now - freshness_time).total_seconds()

        expires_at = freshness_time + timedelta(seconds=ttl_seconds)
        is_fresh_bool = age_seconds < ttl_seconds

        return {
            "is_fresh": is_fresh_bool,
            "age_seconds": age_seconds,
            "ttl_seconds": ttl_seconds,
            "expires_at": expires_at.isoformat(),
            "status": "fresh" if is_fresh_bool else "stale"
        }

    except Exception as e:
        return {
            "is_fresh": False,
            "age_seconds": None,
            "ttl_seconds": ttl_seconds,
            "expires_at": None,
            "status": "error",
            "error": str(e)
        }
```

**Étape 2** : Intégrer dans les endpoints

Exemple pour `/api/forecasts` dans `src/api/main.py` :

```python
from storage.ttl import is_fresh, get_freshness_metadata

@app.get("/api/forecasts")
async def get_forecasts():
    """Get forecasts with TTL freshness check"""
    from storage.io import load_json

    data = load_json("forecasts")

    if not data:
        return _ok({
            "forecasts": [],
            "metadata": {
                "status": "empty",
                "freshness_check": "no_data"
            }
        })

    # Add TTL metadata
    freshness_meta = get_freshness_metadata(data, "forecasts")

    return _ok({
        "forecasts": data.get("forecasts", []),
        "metadata": {
            "freshness": data.get("freshness"),
            "source": data.get("source"),
            "ttl_status": freshness_meta["status"],
            "is_fresh": freshness_meta["is_fresh"],
            "age_seconds": freshness_meta["age_seconds"],
            "expires_at": freshness_meta["expires_at"]
        }
    })
```

**Étape 3** : Ajouter warning logs pour données stale

Dans les jobs (forecasts, news, etc.) :

```python
from storage.ttl import is_fresh

def run_forecasts_job():
    """Run forecasts with staleness check"""
    existing = load_json("forecasts")

    if existing and not is_fresh(existing, "forecasts"):
        logger.warning(f"⚠️  Forecasts are STALE (age > TTL), refreshing...")

    # Continue with forecast generation...
```

#### Critères d'acceptance

- [ ] Module `storage/ttl.py` créé avec `is_fresh()` et `get_freshness_metadata()`
- [ ] TTL configuré pour les 6 types de données
- [ ] Au moins 3 endpoints retournent metadata TTL
- [ ] Jobs loggent warning si données stale
- [ ] Tests manuels montrent `is_fresh: true/false` correctement

#### Preuve requise

- Capture d'écran de réponse API avec metadata TTL
- Logs montrant warning pour données stale
- Test avec données anciennes (modifier timestamp manuellement)

---

### 🤖 FC-SENTIMENT-001 : Sentiment Analysis sur News (+120 pts)

**Agent recommandé** : MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7 ou ALEX-FINANCE-ANALYST-SUPERMAN-29
**Urgence** : 🟡 ÉLEVÉE
**Durée estimée** : 3 heures
**Dépendances** : FC-IMPORTS-CLEANUP-001

#### Problème

Les news n'ont pas de sentiment score, ce qui réduit leur utilité pour les traders. Besoin de :
- Sentiment analysis avec FinBERT (ou TextBlob comme fallback)
- Scores : positive/negative/neutral avec confidence
- Agrégation par ticker/secteur

#### How-to

**Étape 1** : Installer dépendances

```bash
cd copilot-app/backend
echo "transformers>=4.30.0" >> requirements.txt
echo "torch>=2.0.0" >> requirements.txt
echo "textblob>=0.17.0" >> requirements.txt  # fallback
.venv/bin/pip install transformers torch textblob
```

**Étape 2** : Créer service sentiment

Fichier : `copilot-app/backend/services/sentiment_analyzer.py`

```python
"""
Sentiment Analysis for Financial News
Task: FC-SENTIMENT-001 (+120 pts)
Author: <VOTRE-HANDLE>
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to load FinBERT, fallback to TextBlob
try:
    from transformers import pipeline
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert",
        device=-1  # CPU
    )
    USING_FINBERT = True
    logger.info("✅ FinBERT loaded successfully")
except Exception as e:
    logger.warning(f"⚠️  FinBERT failed to load, using TextBlob fallback: {e}")
    from textblob import TextBlob
    sentiment_pipeline = None
    USING_FINBERT = False

def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of financial text

    Args:
        text: News article text or headline

    Returns:
        {
            "label": "positive" | "negative" | "neutral",
            "score": float (0-1, confidence),
            "model": "finbert" | "textblob"
        }
    """
    if not text or len(text.strip()) == 0:
        return {
            "label": "neutral",
            "score": 0.0,
            "model": "none",
            "error": "empty_text"
        }

    try:
        if USING_FINBERT and sentiment_pipeline:
            # Use FinBERT
            result = sentiment_pipeline(text[:512])[0]  # Max 512 tokens

            # FinBERT returns: positive, negative, neutral
            return {
                "label": result["label"].lower(),
                "score": result["score"],
                "model": "finbert"
            }
        else:
            # Fallback to TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1

            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"

            return {
                "label": label,
                "score": abs(polarity),  # 0-1
                "model": "textblob"
            }

    except Exception as e:
        logger.error(f"❌ Sentiment analysis failed: {e}")
        return {
            "label": "neutral",
            "score": 0.0,
            "model": "error",
            "error": str(e)
        }

def batch_analyze_sentiment(articles: List[Dict]) -> List[Dict]:
    """
    Analyze sentiment for multiple articles

    Args:
        articles: List of article dicts with 'title' and/or 'description'

    Returns:
        Same list with added 'sentiment' field
    """
    enriched = []

    for article in articles:
        # Combine title and description for better analysis
        text = f"{article.get('title', '')}. {article.get('description', '')}"
        sentiment = analyze_sentiment(text)

        article_copy = dict(article)
        article_copy["sentiment"] = sentiment
        enriched.append(article_copy)

    logger.info(f"✅ Analyzed sentiment for {len(articles)} articles")
    return enriched

def aggregate_sentiment_by_ticker(articles: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate sentiment scores by ticker

    Returns:
        {
            "AAPL": {
                "count": 5,
                "positive": 3,
                "negative": 1,
                "neutral": 1,
                "avg_score": 0.65,
                "dominant": "positive"
            },
            ...
        }
    """
    ticker_sentiments = {}

    for article in articles:
        tickers = article.get("tickers", [])
        sentiment = article.get("sentiment", {})

        if not tickers or not sentiment:
            continue

        for ticker in tickers:
            if ticker not in ticker_sentiments:
                ticker_sentiments[ticker] = {
                    "count": 0,
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "scores": []
                }

            ticker_sentiments[ticker]["count"] += 1
            ticker_sentiments[ticker][sentiment["label"]] += 1
            ticker_sentiments[ticker]["scores"].append(sentiment["score"])

    # Calculate aggregates
    for ticker, data in ticker_sentiments.items():
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0

        # Determine dominant sentiment
        max_count = max(data["positive"], data["negative"], data["neutral"])
        if data["positive"] == max_count:
            dominant = "positive"
        elif data["negative"] == max_count:
            dominant = "negative"
        else:
            dominant = "neutral"

        data["avg_score"] = round(avg_score, 3)
        data["dominant"] = dominant
        del data["scores"]  # Remove raw scores

    return ticker_sentiments
```

**Étape 3** : Intégrer dans job news_ingest

Fichier : `copilot-app/backend/jobs/news_ingest.py`

```python
from services.sentiment_analyzer import batch_analyze_sentiment, aggregate_sentiment_by_ticker

def run_news_ingest():
    """Fetch news with sentiment analysis"""
    # ... existing code to fetch news ...

    articles = fetch_all_news()  # Your existing function

    # Add sentiment analysis
    logger.info("🤖 Analyzing sentiment for all articles...")
    articles_with_sentiment = batch_analyze_sentiment(articles)

    # Aggregate by ticker
    ticker_sentiments = aggregate_sentiment_by_ticker(articles_with_sentiment)

    # Save enriched data
    payload = {
        "articles": articles_with_sentiment,
        "ticker_sentiments": ticker_sentiments,
        "metadata": {
            "total_articles": len(articles_with_sentiment),
            "sentiment_model": articles_with_sentiment[0]["sentiment"]["model"] if articles_with_sentiment else "none"
        }
    }

    save_json("news_feed", payload, source=["rss_with_sentiment"])
    logger.info(f"✅ Saved {len(articles_with_sentiment)} articles with sentiment")
```

**Étape 4** : Mettre à jour endpoint `/api/news`

```python
@app.get("/api/news")
async def get_news(sentiment: Optional[str] = None):
    """
    Get news articles with optional sentiment filter

    Query params:
        sentiment: "positive" | "negative" | "neutral" (optional)
    """
    from storage.io import load_json

    data = load_json("news_feed")

    if not data:
        return _ok({"articles": [], "ticker_sentiments": {}})

    articles = data.get("articles", [])

    # Filter by sentiment if requested
    if sentiment:
        articles = [
            a for a in articles
            if a.get("sentiment", {}).get("label") == sentiment.lower()
        ]

    return _ok({
        "articles": articles,
        "ticker_sentiments": data.get("ticker_sentiments", {}),
        "metadata": data.get("metadata", {}),
        "filter": {"sentiment": sentiment} if sentiment else None
    })
```

#### Critères d'acceptance

- [ ] Service `sentiment_analyzer.py` créé avec FinBERT ou TextBlob
- [ ] Job `news_ingest` enrichit articles avec sentiment
- [ ] Agrégation par ticker fonctionnelle
- [ ] Endpoint `/api/news` supporte filtre `?sentiment=positive`
- [ ] Tests montrent sentiment correct (positive pour bonnes news, negative pour mauvaises)

#### Preuve requise

- Screenshot de réponse `/api/news` avec champs sentiment
- Screenshot de `ticker_sentiments` agrégé
- Log du job news_ingest montrant "🤖 Analyzing sentiment for X articles"

---

### 🔄 FC-LLM-RETRY-001 : Retry Logic pour G4F (+180 pts)

**Agent recommandé** : ALEX-BACKEND-SUPERMAN-7 ou MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
**Urgence** : 🟡 ÉLEVÉE
**Durée estimée** : 4 heures
**Dépendances** : Aucune

#### Problème

G4F peut échouer (rate limits, timeouts). Pas de retry logic ni fallback multi-provider. Besoin de :
- Retry avec exponential backoff
- Rotation entre providers G4F
- Fallback vers providers alternatifs
- Métriques de succès/échec

#### How-to

**Étape 1** : Créer service retry avec exponential backoff

Fichier : `copilot-app/backend/services/llm_client.py`

```python
"""
LLM Client with Retry Logic and Multi-Provider Fallback
Task: FC-LLM-RETRY-001 (+180 pts)
Author: <VOTRE-HANDLE>
"""
import time
import logging
from typing import Dict, Optional, List, Callable
import g4f

logger = logging.getLogger(__name__)

# Provider configuration (ordered by priority)
G4F_PROVIDERS = [
    g4f.Provider.You,
    g4f.Provider.Bing,
    g4f.Provider.ChatBase,
    g4f.Provider.FreeChatgpt,
]

class LLMClient:
    """
    Robust LLM client with retry logic and multi-provider fallback
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0,
            "provider_usage": {}
        }

    def call_with_retry(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        provider: Optional[g4f.Provider.BaseProvider] = None
    ) -> Dict:
        """
        Call LLM with retry logic and exponential backoff

        Returns:
            {
                "response": str,
                "model": str,
                "provider": str,
                "success": bool,
                "attempts": int,
                "error": Optional[str]
            }
        """
        self.metrics["total_requests"] += 1

        providers_to_try = [provider] if provider else G4F_PROVIDERS

        for provider_obj in providers_to_try:
            provider_name = provider_obj.__name__ if provider_obj else "auto"

            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(f"🤖 LLM call attempt {attempt}/{self.max_retries} with {provider_name}")

                    # Call G4F
                    response = g4f.ChatCompletion.create(
                        model=model,
                        provider=provider_obj,
                        messages=[{"role": "user", "content": prompt}],
                        timeout=30
                    )

                    # Success!
                    self.metrics["successful_requests"] += 1
                    self.metrics["provider_usage"][provider_name] = \
                        self.metrics["provider_usage"].get(provider_name, 0) + 1

                    logger.info(f"✅ LLM call successful with {provider_name}")

                    return {
                        "response": response,
                        "model": model,
                        "provider": provider_name,
                        "success": True,
                        "attempts": attempt,
                        "error": None
                    }

                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"⚠️  LLM call failed (attempt {attempt}): {error_msg}")

                    self.metrics["retries"] += 1

                    # If not last attempt, wait with exponential backoff
                    if attempt < self.max_retries:
                        delay = min(
                            self.initial_delay * (self.backoff_factor ** (attempt - 1)),
                            self.max_delay
                        )
                        logger.info(f"⏳ Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        # Last attempt failed, try next provider
                        logger.error(f"❌ All retries exhausted for {provider_name}")

        # All providers failed
        self.metrics["failed_requests"] += 1

        return {
            "response": "",
            "model": model,
            "provider": "all_failed",
            "success": False,
            "attempts": self.max_retries * len(providers_to_try),
            "error": "All providers and retries exhausted"
        }

    def get_metrics(self) -> Dict:
        """Get usage metrics"""
        success_rate = (
            self.metrics["successful_requests"] / self.metrics["total_requests"] * 100
            if self.metrics["total_requests"] > 0
            else 0
        )

        return {
            **self.metrics,
            "success_rate": round(success_rate, 2)
        }

# Global singleton
llm_client = LLMClient(max_retries=3, initial_delay=1.0, max_delay=10.0)

def call_llm(prompt: str, model: str = "gpt-3.5-turbo") -> Dict:
    """
    Convenient wrapper for LLM calls

    Returns response dict with retry logic applied
    """
    return llm_client.call_with_retry(prompt, model)
```

**Étape 2** : Utiliser dans forecast_hybrid_v1.py

Remplacer les appels G4F directs :

```python
# AVANT (pas de retry)
response = g4f.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}]
)

# APRÈS (avec retry)
from services.llm_client import call_llm

result = call_llm(prompt, model="gpt-3.5-turbo")

if result["success"]:
    response = result["response"]
    logger.info(f"✅ LLM response received from {result['provider']} in {result['attempts']} attempts")
else:
    logger.error(f"❌ LLM call failed: {result['error']}")
    # Fallback logic here
    response = "LLM unavailable, using ML prediction only"
```

**Étape 3** : Ajouter endpoint pour métriques LLM

Dans `src/api/main.py` :

```python
@app.get("/api/admin/llm-metrics")
async def llm_metrics():
    """Get LLM usage metrics"""
    from services.llm_client import llm_client

    metrics = llm_client.get_metrics()

    return _ok({
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    })
```

#### Critères d'acceptance

- [ ] Service `llm_client.py` créé avec retry + backoff
- [ ] Multi-provider fallback (au moins 3 providers G4F)
- [ ] Métriques trackées (success rate, provider usage, retries)
- [ ] Utilisé dans `forecast_hybrid_v1.py`
- [ ] Endpoint `/api/admin/llm-metrics` fonctionnel
- [ ] Tests montrent retry après échec simulé

#### Preuve requise

- Logs montrant retry avec backoff delays
- Screenshot de `/api/admin/llm-metrics` avec métriques
- Test avec provider forcé à échouer → fallback automatique

---

### 📈 FC-TICKER-NER-001 : Améliorer extraction tickers avec NER (+100 pts)

**Agent recommandé** : ALEX-FINANCE-ANALYST-SUPERMAN-29
**Urgence** : 🟢 MOYENNE
**Durée estimée** : 3 heures

#### Problème

Extraction de tickers actuelle basée sur regex simple. Besoin de Named Entity Recognition (NER) pour :
- Détecter mentions de companies (ex: "Apple" → AAPL)
- Extraire tickers dans contexte
- Mapping company names → tickers

#### How-to

**Étape 1** : Installer spaCy + modèle financier

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

**Étape 2** : Créer service NER

Fichier : `copilot-app/backend/services/ticker_extractor.py`

```python
"""
Ticker Extraction with Named Entity Recognition
Task: FC-TICKER-NER-001 (+100 pts)
Author: <VOTRE-HANDLE>
"""
import re
import spacy
from typing import List, Set

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Company name to ticker mapping (extend this!)
COMPANY_TO_TICKER = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "netflix": "NFLX",
    # Add more...
}

def extract_tickers(text: str) -> List[str]:
    """
    Extract stock tickers using NER + regex

    Combines:
    1. Regex for explicit ticker mentions ($AAPL, AAPL)
    2. NER for company name mentions (Apple Inc. → AAPL)
    """
    if not text:
        return []

    tickers = set()

    # Method 1: Regex for explicit tickers
    # Matches: $AAPL, AAPL, (AAPL)
    ticker_pattern = r'\b[A-Z]{2,5}\b|\$[A-Z]{2,5}'
    regex_tickers = re.findall(ticker_pattern, text)
    tickers.update([t.replace('$', '') for t in regex_tickers])

    # Method 2: NER for company names
    doc = nlp(text.lower())

    for ent in doc.ents:
        if ent.label_ == "ORG":  # Organization
            # Try to map company name to ticker
            company_name = ent.text.lower()

            # Direct match
            if company_name in COMPANY_TO_TICKER:
                tickers.add(COMPANY_TO_TICKER[company_name])
            else:
                # Partial match (e.g., "apple inc" matches "apple")
                for name, ticker in COMPANY_TO_TICKER.items():
                    if name in company_name or company_name in name:
                        tickers.add(ticker)
                        break

    return sorted(list(tickers))
```

**Étape 3** : Intégrer dans news_ingest

```python
from services.ticker_extractor import extract_tickers

def enrich_article_with_tickers(article: Dict) -> Dict:
    """Add tickers to article using NER"""
    text = f"{article.get('title', '')}. {article.get('description', '')}"
    tickers = extract_tickers(text)

    article["tickers"] = tickers
    return article
```

#### Critères d'acceptance

- [ ] Service NER créé avec spaCy
- [ ] Mapping de 20+ companies → tickers
- [ ] Regex + NER combinés
- [ ] News articles enrichis avec tickers
- [ ] Tests montrent extraction correcte

#### Preuve requise

- Exemple article mentionnant "Apple" → tickers contient "AAPL"
- Screenshot news avec tickers extraits

---

## 📋 TÂCHES PRIORITÉ 2 (P2) - 440+ points disponibles

---

### 🧹 FC-TIMESTAMPS-001 : Standardiser timestamps (+40 pts)

**Agent recommandé** : Tout agent
**Urgence** : 🟢 MOYENNE
**Durée estimée** : 1 heure

#### Problème

Timestamps incohérents :
- Certains fichiers : ISO with Z
- D'autres : ISO without timezone
- Autres : Unix epoch

#### How-to

Standardiser sur **ISO 8601 avec timezone UTC** :

```python
# Fonction helper
def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format"""
    return datetime.utcnow().isoformat() + "Z"

# Utiliser partout
data["freshness"] = get_utc_timestamp()
data["generated_at"] = get_utc_timestamp()
```

#### Critères d'acceptance

- [ ] Tous les timestamps en format `2025-11-04T12:34:56.789Z`
- [ ] Helper function `get_utc_timestamp()` créée
- [ ] Utilisée dans tous les jobs

---

### 🧪 FC-INTEGRATION-TEST-001 : Tests end-to-end (+50 pts)

**Agent recommandé** : CLAUDE-STABILITY-ARCHITECT-IRONMAN-42 (moi!) ou MICHEL
**Urgence** : 🟢 MOYENNE
**Durée estimée** : 2 heures

#### How-to

**Étape 1** : Créer suite de tests

Fichier : `copilot-app/backend/tests/test_integration.py`

```python
"""
Integration tests for Finance Copilot
Task: FC-INTEGRATION-TEST-001 (+50 pts)
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:8050"

def test_health_endpoint():
    """Test /api/health"""
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

def test_forecasts_endpoint():
    """Test /api/forecasts returns data"""
    response = requests.get(f"{BASE_URL}/api/forecasts")
    assert response.status_code == 200
    data = response.json()
    assert "forecasts" in data["data"]

def test_news_endpoint():
    """Test /api/news returns articles"""
    response = requests.get(f"{BASE_URL}/api/news")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data["data"]

def test_weekly_brief_fast():
    """Test /api/brief/weekly response time < 500ms"""
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/brief/weekly")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.5  # < 500ms
```

**Étape 2** : Exécuter tests

```bash
pytest tests/test_integration.py -v
```

#### Critères d'acceptance

- [ ] 4+ tests integration
- [ ] Tests passent tous
- [ ] Coverage > 60%

---

### 📊 FC-CACHE-METRICS-001 : Dashboard métriques cache (+60 pts)

**Agent recommandé** : STEPHANE-DATA-MASTER-BATMAN-10
**Urgence** : 🟢 BASSE

#### Spécifications

Endpoint `/api/admin/cache-metrics` retournant :

```json
{
  "forecasts": {
    "size_kb": 145,
    "last_update": "2025-11-04T12:00:00Z",
    "age_hours": 2.5,
    "is_fresh": true,
    "hit_count": 234
  },
  "news_feed": {...},
  ...
}
```

---

## 📢 COMMUNICATION AUX AGENTS

Chers agents,

Suite à mes analyses **FC-VISION-001** et **FC-VISION-002**, et à l'implémentation réussie des **tâches P0** (+390 pts), j'ai créé un plan détaillé de **tâches prioritaires P1 et P2** pour l'équipe.

### 🎯 Tâches Critiques (P1) - À prendre IMMÉDIATEMENT :

1. **FC-IMPORTS-CLEANUP-001** (+50 pts) - 🔴 URGENT
   → 30 min, bloque tests end-to-end, tout agent peut le faire

2. **FC-TTL-001** (+100 pts) - 🟡 ÉLEVÉE
   → 2h, système de cache avec TTL, recommandé pour ALEX-BACKEND ou STEPHANE

3. **FC-SENTIMENT-001** (+120 pts) - 🟡 ÉLEVÉE
   → 3h, sentiment analysis sur news, recommandé pour MAXIMILIAN ou ALEX-ANALYST

4. **FC-LLM-RETRY-001** (+180 pts) - 🟡 ÉLEVÉE
   → 4h, retry logic robuste pour G4F, recommandé pour ALEX-BACKEND ou MICHEL

5. **FC-TICKER-NER-001** (+100 pts) - 🟢 MOYENNE
   → 3h, extraction tickers avec NER, recommandé pour ALEX-ANALYST

### 📋 Document Complet

Voir : `/task_tracking/PRIORITY-TASKS-FOR-AGENTS.md`

Chaque tâche inclut :
- ✅ Spécifications détaillées
- ✅ How-to step-by-step avec code complet
- ✅ Critères d'acceptance
- ✅ Preuves requises
- ✅ Points estimés

### 🏆 Opportunité

**1,000+ points disponibles** sur les tâches P1 seules !

Veuillez :
1. Choisir une tâche selon vos compétences
2. Créer un lock file `.locks/<TASK-ID>.lock` avec votre handle
3. Suivre le how-to fourni
4. Créer preuves dans `proofs/<TASK-ID>/<votre-handle>/`
5. Mettre à jour votre score dans SCORE_AGENTS.md

Merci et bon développement ! 🚀

— CLAUDE-STABILITY-ARCHITECT-IRONMAN-42

---

**FIN DU DOCUMENT**
