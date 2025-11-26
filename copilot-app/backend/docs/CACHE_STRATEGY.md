# 🗄️ STRATÉGIE CACHE - QUAND ET COMMENT

**Date :** 2025-11-25 22:59  
**Statut actuel :** ❌ **PAS DE CACHE** (live-only)

---

## 🎯 RÈGLE D'OR

> **On ne met PAS de cache tant que le risque de vieillissement n'est pas maîtrisé.**

**Principe :** Mieux vaut échouer explicitement que servir des prévisions basées sur des données périmées.

---

## 📊 ANALYSE PAR TYPE DE DONNÉES

### **1. DONNÉES LIVE-ONLY (Jamais de cache)**

| Source | Fréquence | Pourquoi live-only | Impact si périmé |
|--------|-----------|-------------------|------------------|
| **Prix actions** (yfinance) | Real-time | Market mouvant | ⚠️ **CRITIQUE** - Prévisions invalides |
| **News sentiment** | Minutes | Breaking news | ⚠️ **CRITIQUE** - Sentiment obsolète |
| **VIX** (volatilité) | 15min | Indicateur marché | ⚠️ **CRITIQUE** - Risk assessment faux |
| **LLM verdict** | À la demande | Synthèse contextuelle | ⚠️ **CRITIQUE** - Décision obsolète |

**Verdict :** ❌ **PAS DE CACHE, JAMAIS**

---

### **2. DONNÉES SEMI-STATIQUES (Cache acceptable avec contrôle strict)**

| Source | Fréquence MAJ | TTL Max Acceptable | Vérification |
|--------|---------------|-------------------|--------------|
| **Taux 10Y US** (FRED) | Daily (16h ET) | 6h | Timestamp + rejet si > 6h |
| **CPI** (FRED) | Monthly | 24h | Timestamp + rejet si > 24h |
| **DXY** (USD Index) | Daily | 12h | Timestamp + rejet si > 12h |
| **Commodities** (Gold/WTI) | Daily | 12h | Timestamp + rejet si > 12h |

**Verdict :** ⚠️ **Cache possible** avec conditions strictes

**Conditions requises :**
1. ✅ Timestamp explicite dans données
2. ✅ Rejet strict si `age > TTL`
3. ✅ Log explicite `"cache_hit_fresh"` ou `"cache_rejected_stale"`
4. ✅ Fallback sur fetch live si rejeté
5. ✅ Alerting si taux de rejet > 10%

---

### **3. DONNÉES STATIQUES (Cache long acceptable)**

| Source | Fréquence MAJ | TTL Max | Impact si périmé |
|--------|---------------|---------|------------------|
| **Ownership** (sector, PE, beta) | Weekly | 7 jours | ℹ️ **FAIBLE** - Contexte général |
| **Market cap** | Weekly | 7 jours | ℹ️ **FAIBLE** - Classification |
| **Company fundamentals** (revenue) | Quarterly | 30 jours | ℹ️ **FAIBLE** - Trend long-terme |

**Verdict :** ✅ **Cache acceptable** (longue durée)

**Conditions :**
- Timestamp obligatoire
- Rejet si `age > TTL`
- Utilisation pour **contexte seulement**, pas pour prévision directe

---

## 🔧 IMPLÉMENTATION CACHE SÛRE (Future)

### **Architecture Proposée**

```python
# src/services/safe_cache.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
import structlog

logger = structlog.get_logger()

@dataclass
class CacheConfig:
    """Configuration par type de donnée."""
    name: str
    ttl_hours: float
    allow_stale: bool = False  # Si True, log warning mais serve
    critical: bool = True       # Si True, FAIL si stale

class SafeCache:
    """
    Cache avec vérification stricte de fraîcheur.
    
    Rules:
    - NEVER serve stale data for critical sources
    - ALWAYS log cache status (hit/miss/stale)
    - ALWAYS check timestamp before serving
    - FAIL explicitly if critical data is stale
    """
    
    def __init__(self):
        self.configs = {
            # Jamais de cache
            "prices": CacheConfig("prices", ttl_hours=0, critical=True),
            "news": CacheConfig("news", ttl_hours=0, critical=True),
            "vix": CacheConfig("vix", ttl_hours=0, critical=True),
            
            # Cache court (semi-static)
            "rates_10y": CacheConfig("rates_10y", ttl_hours=6, critical=True),
            "cpi": CacheConfig("cpi", ttl_hours=24, critical=True),
            "dxy": CacheConfig("dxy", ttl_hours=12, critical=True),
            
            # Cache long (static)
            "ownership": CacheConfig("ownership", ttl_hours=168, critical=False),  # 7 days
            "fundamentals": CacheConfig("fundamentals", ttl_hours=720, critical=False),  # 30 days
        }
    
    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable,
        config_name: str
    ) -> Dict[str, Any]:
        """
        Get from cache or fetch live, with strict freshness check.
        
        Args:
            key: Cache key
            fetcher: Function to fetch live data
            config_name: Name in self.configs
        
        Returns:
            Fresh data
        
        Raises:
            ValueError: If critical data is stale and can't be fetched
        """
        config = self.configs.get(config_name)
        if not config:
            raise ValueError(f"Unknown cache config: {config_name}")
        
        # If TTL = 0, always fetch live
        if config.ttl_hours == 0:
            logger.info("cache_skip_live_only", key=key, source=config.name)
            return await fetcher()
        
        # Try cache
        cached = await self._get_from_cache(key)
        
        if cached:
            # Check freshness
            age_hours = self._calculate_age(cached)
            
            if age_hours <= config.ttl_hours:
                # Fresh cache hit
                logger.info(
                    "cache_hit_fresh",
                    key=key,
                    source=config.name,
                    age_hours=round(age_hours, 2),
                    ttl_hours=config.ttl_hours
                )
                return cached["data"]
            
            else:
                # Stale cache
                logger.warning(
                    "cache_rejected_stale",
                    key=key,
                    source=config.name,
                    age_hours=round(age_hours, 2),
                    ttl_hours=config.ttl_hours,
                    critical=config.critical
                )
                
                if config.critical and not config.allow_stale:
                    # Critical data: MUST fetch fresh
                    try:
                        fresh_data = await fetcher()
                        await self._set_cache(key, fresh_data)
                        logger.info("cache_refreshed", key=key, source=config.name)
                        return fresh_data
                    except Exception as e:
                        # Fetch failed: FAIL explicitly
                        raise ValueError(
                            f"Critical data {config.name} is stale ({age_hours:.1f}h > {config.ttl_hours}h) "
                            f"and fresh fetch failed: {e}"
                        )
        
        # No cache or stale: fetch live
        logger.info("cache_miss", key=key, source=config.name)
        
        try:
            fresh_data = await fetcher()
            await self._set_cache(key, fresh_data)
            return fresh_data
        except Exception as e:
            logger.error("fetch_failed", key=key, source=config.name, error=str(e))
            raise
    
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from Redis/file cache."""
        # Implementation: Redis or file-based
        pass
    
    async def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Set in cache with timestamp."""
        cached = {
            "data": data,
            "cached_at": datetime.utcnow().isoformat() + "Z"
        }
        # Implementation: Redis or file-based
        pass
    
    def _calculate_age(self, cached: Dict[str, Any]) -> float:
        """Calculate age in hours."""
        cached_at_str = cached.get("cached_at")
        if not cached_at_str:
            return float('inf')  # No timestamp = infinitely old
        
        cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
        age_seconds = (datetime.utcnow() - cached_at).total_seconds()
        return age_seconds / 3600


# Usage example
cache = SafeCache()

# Prices: NEVER cached (TTL=0)
prices = await cache.get_or_fetch(
    key="prices:AAPL",
    fetcher=lambda: fetch_yfinance_prices("AAPL"),
    config_name="prices"
)
# → ALWAYS fetches live

# Rates: Cached 6h, FAIL if stale and can't refresh
rates = await cache.get_or_fetch(
    key="rates:10y",
    fetcher=lambda: fetch_fred_rates("DGS10"),
    config_name="rates_10y"
)
# → Cache hit if fresh (<6h)
# → Fetch live if stale (>6h)
# → FAIL if stale AND fetch fails

# Ownership: Cached 7 days, not critical
ownership = await cache.get_or_fetch(
    key="ownership:AAPL",
    fetcher=lambda: fetch_yahoo_ownership("AAPL"),
    config_name="ownership"
)
# → Cache hit if fresh (<7 days)
# → Fetch live if stale
```

---

## 📊 GARANTIES DE QUALITÉ

### **Validation de Fraîcheur**

```python
def validate_freshness(data: Dict[str, Any], source: str, max_age_hours: float):
    """
    Validate data freshness before using in predictions.
    
    Raises:
        ValueError: If data is too stale for quality predictions
    """
    timestamp_keys = ["cached_at", "fetched_at", "generated_at", "computed_at"]
    ts = None
    
    for key in timestamp_keys:
        if key in data:
            ts = datetime.fromisoformat(data[key].replace("Z", "+00:00"))
            break
    
    if not ts:
        raise ValueError(f"{source}: No timestamp found, cannot validate freshness")
    
    age_hours = (datetime.utcnow() - ts).total_seconds() / 3600
    
    if age_hours > max_age_hours:
        raise ValueError(
            f"{source}: Data too stale for quality predictions. "
            f"Age: {age_hours:.1f}h, Max: {max_age_hours}h. "
            f"Fetch fresh data or reduce TTL."
        )
    
    logger.info(
        "freshness_validated",
        source=source,
        age_hours=round(age_hours, 2),
        max_age_hours=max_age_hours,
        status="OK"
    )
```

### **Alerting sur Cache Stale**

```python
@dataclass
class CacheMetrics:
    """Metrics pour monitoring cache health."""
    source: str
    period_hours: float = 24.0
    
    total_requests: int = 0
    cache_hits_fresh: int = 0
    cache_rejected_stale: int = 0
    cache_miss: int = 0
    fetch_failures: int = 0
    
    @property
    def stale_rate(self) -> float:
        """% of requests that hit stale cache."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_rejected_stale / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """% of fetch attempts that failed."""
        attempts = self.cache_miss + self.cache_rejected_stale
        if attempts == 0:
            return 0.0
        return self.fetch_failures / attempts
    
    def should_alert(self) -> bool:
        """Alert if stale rate > 10% or failure rate > 5%."""
        return self.stale_rate > 0.10 or self.failure_rate > 0.05

# Monitor cache health
metrics = CacheMetrics(source="rates_10y", period_hours=24)

if metrics.should_alert():
    logger.error(
        "cache_health_degraded",
        source=metrics.source,
        stale_rate=f"{metrics.stale_rate:.1%}",
        failure_rate=f"{metrics.failure_rate:.1%}"
    )
    # → Alert ops team
```

---

## 🎯 DÉCISION: QUAND ACTIVER LE CACHE ?

### **Critères d'Activation**

Le cache peut être activé **UNIQUEMENT** si :

1. ✅ **Monitoring en place**
   - Logs structurés (hit/miss/stale)
   - Métriques par source (stale rate, failure rate)
   - Alerting si dégradation

2. ✅ **Tests validés**
   - Test: données fraîches → cache hit
   - Test: données stales → rejet + fetch
   - Test: fetch échoue → FAIL explicite
   - Test: TTL=0 → toujours live

3. ✅ **Validation qualité**
   - Comparaison prévisions avec/sans cache
   - Aucune dégradation de qualité détectée
   - Latence acceptable même sans cache

4. ✅ **ROI positif**
   - Gain latence > 30%
   - Réduction coûts API > $100/mois
   - Pas de perte de qualité

### **Phase de Déploiement**

**Phase 1 : Monitoring Only (2 semaines)**
```python
# Log cache opportunities mais ne cache pas
logger.info("cache_opportunity", source=source, would_cache=True, ttl_hours=6)
# → Mesure combien on gagnerait sans risquer la qualité
```

**Phase 2 : Cache Non-Critical (2 semaines)**
```python
# Active cache UNIQUEMENT pour ownership/fundamentals
cache.get_or_fetch(..., config_name="ownership")  # TTL=7 days
# → Pas d'impact qualité, gain latence
```

**Phase 3 : Cache Semi-Static (2 semaines)**
```python
# Active cache pour rates/CPI/DXY avec TTL court
cache.get_or_fetch(..., config_name="rates_10y")  # TTL=6h
# → Monitor qualité prévisions
```

**Phase 4 : Validation Finale**
- Comparaison A/B: prévisions avec/sans cache
- Si qualité identique + gain latence → garder
- Si qualité dégradée → désactiver

---

## 🚫 JAMAIS DE CACHE POUR

| Source | Raison |
|--------|--------|
| **Prix real-time** | Market mouvant, obsolète en secondes |
| **News sentiment** | Breaking news change tout |
| **VIX** | Volatilité = risque, doit être actuel |
| **LLM verdicts** | Contexte change constamment |
| **ML priors** | Basé sur prix récents, doit être live |

---

## ✅ VERDICT ACTUEL

**Status :** ❌ **PAS DE CACHE ACTIVÉ**

**Raison :** Risque de vieillissement pas encore maîtrisé

**Prochaines étapes** :
1. Implémenter `SafeCache` (6h)
2. Phase 1 monitoring (2 sem)
3. Tests qualité (1 sem)
4. Décision data-driven

**Activation :** Uniquement si validation qualité OK + ROI positif

---

**Date de révision :** À définir après Phase 1 monitoring
