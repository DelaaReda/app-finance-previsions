"""
Recommendations Service - ML + LLM powered daily recommendations

Generates top 3 daily actionable recommendations by combining:
- ML ranking (5-factor scoring)
- LLM validation & reasoning
- Macro alignment
- Risk assessment

Author: ELENA-39
Task: FC-INT-023
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from domains.judge.application.g4f_client import call_llm  # type: ignore
except Exception:
    try:
        from services.g4f_client import call_llm  # type: ignore
    except Exception:
        call_llm = None  # type: ignore

# Internal services
try:
    from domains.judge.application.intelligence_service import get_intelligence_service
except ImportError:
    get_intelligence_service = None

try:
    from domains.copilot.application.context_service import get_context_service
except ImportError:
    get_context_service = None

# Strategy playbooks integration (BATCH-15-DEV-02)
try:
    from domains.copilot.application.playbook_resolver import get_playbook_resolver
    from domains.copilot.domain.playbook import RiskProfile
except ImportError:
    get_playbook_resolver = None
    RiskProfile = None

# Storage
try:
    from storage.io import load_json
    def load_forecasts():
        """Load forecasts from storage"""
        data = load_json("forecasts")
        if data and "data" in data:
            return data
        return None
except ImportError:
    load_forecasts = None


class RecommendationsService:
    """
    Smart Recommendations Service
    
    Combines ML ranking with LLM validation to generate
    actionable daily recommendations.
    
    Features:
    - 5-factor ML scoring
    - LLM-powered reasoning
    - Macro-aware recommendations
    - 24h caching
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        if call_llm is None:
            self.logger.warning("call_llm unavailable, using simulated validation")

        # Services
        if get_intelligence_service:
            self.intelligence_service = get_intelligence_service()
        else:
            self.intelligence_service = None

        if get_context_service:
            self.context_service = get_context_service()
        else:
            self.context_service = None

        # Strategy playbooks resolver (BATCH-15-DEV-02)
        if get_playbook_resolver:
            self.playbook_resolver = get_playbook_resolver()
        else:
            self.playbook_resolver = None
    
    async def generate_daily_recommendations(
        self,
        universe: Optional[List[str]] = None,
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        Generate top N daily recommendations
        
        Args:
            universe: Optional list of tickers to consider
            limit: Number of recommendations (1-10)
        
        Returns:
            Dict with recommendations and market context
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"💡 generate_daily_recommendations called", extra={
            "universe": universe,
            "universe_count": len(universe) if universe else 0,
            "limit": limit
        })
        
        try:
            # Check cache (24h validity)
            cache_key = f"recommendations_daily_{universe}_{limit}" if universe else f"recommendations_daily_default_{limit}"
            self.logger.debug(f"🔍 Checking cache: {cache_key}")
            cached = self._load_cache(cache_key)
            if cached:
                self.logger.info(f"✅ Returning cached recommendations", extra={
                    "cache_key": cache_key,
                    "recommendations_count": len(cached.get("recommendations", []))
                })
                return cached
            self.logger.debug(f"⚠️ No cache found, generating new recommendations")
            
            # Default universe
            if not universe:
                universe = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA', 'SPY', 'QQQ', 'TLT', 'GLD', 'JNJ', 'PG']
                self.logger.debug(f"📋 Using default universe: {len(universe)} tickers")
            else:
                self.logger.debug(f"📋 Using provided universe: {len(universe)} tickers")
            
            # Aggregate data
            self.logger.debug(f"🔄 Aggregating data for {len(universe)} tickers...")
            data = await self._aggregate_data(universe)
            self.logger.debug(f"✅ Data aggregated", extra={
                "tickers_with_data": len([k for k in data.keys() if k != 'market_context']),
                "has_market_context": 'market_context' in data
            })
            
            # Calculate ML scores
            self.logger.debug(f"🧮 Calculating ML scores...")
            candidates = []
            for ticker in universe:
                try:
                    score = self._calculate_ml_score(ticker, data)
                    candidates.append({
                        'ticker': ticker,
                        'score': score,
                        'data': data.get(ticker, {})
                    })
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to score {ticker}: {e}", extra={
                        "ticker": ticker,
                        "error": str(e)
                    })
            
            self.logger.info(f"📊 ML scores calculated", extra={
                "candidates_count": len(candidates),
                "top_scores": sorted([c['score'] for c in candidates], reverse=True)[:5] if candidates else []
            })

            # Sort by score and keep the most relevant ones
            self.logger.debug(f"🔀 Sorting candidates by score...")
            candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
            
            # Lower threshold if no high-scoring candidates
            filtered = [c for c in candidates if c['score'] >= 0.35]
            if not filtered and candidates:
                self.logger.debug(f"⚠️ No candidates with score >= 0.35, lowering threshold to 0.20")
                # Lower threshold to 0.20 if no high-scoring candidates
                filtered = [c for c in candidates if c['score'] >= 0.20]
            if not filtered and candidates:
                self.logger.debug(f"⚠️ No candidates with score >= 0.20, lowering threshold to 0.10")
                # Even lower threshold to 0.10 if still no candidates
                filtered = [c for c in candidates if c['score'] >= 0.10]
            if not filtered and candidates:
                self.logger.debug(f"⚠️ No candidates with score >= 0.10, taking top {max(1, limit)} candidates")
                # Take top candidates regardless of score if we have any
                filtered = candidates[:max(1, limit)]
            
            if filtered:
                candidates = filtered
                self.logger.debug(f"✅ Filtered to {len(candidates)} candidates")
            elif candidates:
                candidates = candidates[: max(1, limit)]
                self.logger.debug(f"✅ Using top {len(candidates)} candidates")

            # LLM validation (top candidates) - but skip if no candidates
            self.logger.debug(f"🤖 Starting LLM validation for top {min(len(candidates), limit * 2)} candidates...")
            validated = []
            if candidates:
                for i, candidate in enumerate(candidates[:limit * 2]):  # Over-select for validation
                    self.logger.debug(f"🤖 Validating candidate {i+1}/{min(len(candidates), limit * 2)}: {candidate['ticker']} (score: {candidate['score']:.3f})")
                    try:
                        validation = await self._validate_with_llm(
                            candidate['ticker'],
                            candidate['score'],
                            data
                        )
                        
                        # Accept if approved OR if LLM validation fails (fallback to ML score)
                        if validation.get('decision') == 'APPROVE' or not validation.get('decision'):
                            self.logger.debug(f"✅ {candidate['ticker']} approved by LLM")
                            validated.append({
                                **candidate,
                                **validation
                            })
                        else:
                            self.logger.debug(f"❌ {candidate['ticker']} rejected by LLM: {validation.get('decision')}")
                    except Exception as e:
                        # If LLM validation fails, still include the candidate based on ML score
                        self.logger.warning(f"⚠️ LLM validation failed for {candidate['ticker']}: {e}, using ML score", extra={
                            "ticker": candidate['ticker'],
                            "error": str(e)
                        })
                        validated.append({
                            **candidate,
                            'decision': 'APPROVE',
                            'reasoning': f"ML score: {candidate['score']:.2f}",
                            'confidence': candidate['score']
                        })
                    
                    if len(validated) >= limit:
                        self.logger.debug(f"✅ Reached limit of {limit} validated recommendations")
                        break
            
            self.logger.info(f"✅ LLM validation complete", extra={
                "validated_count": len(validated),
                "requested_limit": limit
            })
            
            # Format output - use validated or fallback to candidates if no validated
            if validated:
                self.logger.debug(f"📝 Formatting {len(validated[:limit])} validated recommendations...")
                result = self._format_recommendations(
                    validated[:limit],
                    data.get('market_context', {})
                )
            elif candidates:
                self.logger.debug(f"📝 Formatting {len(candidates[:limit])} candidates (no LLM validation)...")
                # Format candidates even without LLM validation
                result = self._format_recommendations(
                    candidates[:limit],
                    data.get('market_context', {})
                )
            else:
                self.logger.warning(f"⚠️ No candidates found, using fallback recommendations")
                # No candidates at all - use fallback
                result = self._fallback_recommendations()
            
            import time
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            
            # Save to cache only if we have recommendations
            if result.get('recommendations'):
                self.logger.debug(f"💾 Saving to cache: {cache_key}")
                self._save_cache(cache_key, result)
                self.logger.debug(f"✅ Recommendations cached")
            
            self.logger.info(f"✅ Recommendations generated successfully", extra={
                "elapsed_seconds": round(elapsed, 3),
                "recommendations_count": len(result.get('recommendations', [])),
                "market_regime": result.get('market_context', {}).get('regime', 'N/A'),
                "used_llm_validation": len(validated) > 0 if 'validated' in locals() else False
            })
            
            return result
            
        except Exception as e:
            import time
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            self.logger.error(f"❌ Failed to generate recommendations: {e}", exc_info=True, extra={
                "error_type": type(e).__name__,
                "elapsed_seconds": round(elapsed, 3),
                "universe": universe,
                "limit": limit
            })
            return self._fallback_recommendations()
    
    async def _aggregate_data(self, universe: List[str]) -> Dict[str, Any]:
        """Aggregate data from all sources"""
        data = {
            'market_context': {},
            'forecasts': {},
            'macro': {},
            'news': {}
        }
        
        try:
            # Get market context
            if self.context_service:
                context = await self.context_service.get_current_market_context()
                data['market_context'] = context
            
            # Get intelligence
            if self.intelligence_service:
                intelligence = await self.intelligence_service.get_market_snapshot_intelligence()
                data['intelligence'] = intelligence
            
            # Get forecasts
            if load_forecasts:
                forecasts_data = load_forecasts()
                if forecasts_data and 'data' in forecasts_data:
                    rows = forecasts_data['data'].get('rows', [])
                    for row in rows:
                        ticker = row.get('ticker') or row.get('symbol')
                        if ticker in universe:
                            data['forecasts'][ticker] = row
            
        except Exception as e:
            self.logger.warning(f"Data aggregation partially failed: {e}")
        
        # Add ticker-specific data
        for ticker in universe:
            data[ticker] = {
                'forecast': data['forecasts'].get(ticker, {}),
                'ticker': ticker
            }

        return data

    def _calculate_ml_score(
        self,
        ticker: str,
        data: Dict[str, Any]
    ) -> float:
        """
        Calculate ML ranking score (5 factors)

        Score = (
            forecast_confidence * 0.35 +
            momentum_strength * 0.25 +
            news_sentiment * 0.20 +
            macro_alignment * 0.15 +
            risk_reward_ratio * 0.05
        )
        """
        try:
            ticker_data = data.get(ticker, {})
            forecast = ticker_data.get('forecast', {})
            market_context = data.get('market_context', {})

            # 1. Forecast confidence (0.35)
            forecast_conf = float(forecast.get('confidence', 0.5) or 0.5)

            # Expected return normalized (-5% to +5% window)
            expected_return = float(forecast.get('expected_return', 0.0) or 0.0)
            exp_score = self._normalize(expected_return, -0.05, 0.05)

            # 2. Momentum strength (0.25)
            direction = (forecast.get('direction') or '').lower()
            if direction == 'up':
                momentum = 0.8
            elif direction == 'down':
                momentum = 0.2
            else:
                momentum = 0.5

            # 3. News sentiment (0.20)
            ctx = forecast.get('market_context', {})
            news_sentiment = self._normalize(ctx.get('news_sentiment'), -0.6, 0.6)
            news_volume = self._normalize(ctx.get('news_volume_zscore'), -3, 3)
            news_score = (news_sentiment * 0.7) + (news_volume * 0.3)

            # 4. Macro alignment (0.15)
            alignment = self._calculate_macro_alignment(
                ticker,
                forecast.get('direction', 'flat'),
                market_context.get('regime', 'NORMAL')
            )

            # 5. Risk-reward ratio (0.05)
            risk_reward = self._normalize(abs(expected_return), 0, 0.08)

            # Weighted sum
            score = (
                forecast_conf * 0.30 +
                exp_score * 0.20 +
                momentum * 0.20 +
                news_score * 0.15 +
                alignment * 0.10 +
                risk_reward * 0.05
            )

            return min(1.0, max(0.0, score))

        except Exception as e:
            self.logger.warning(f"ML scoring failed for {ticker}: {e}")
            return 0.5

    @staticmethod
    def _normalize(value: Optional[Any], lower: float, upper: float, default: float = 0.5) -> float:
        """Map value into [0,1] range with clipping."""
        if value is None:
            return default
        try:
            val = float(value)
        except (TypeError, ValueError):
            return default
        if upper == lower:
            return default
        val = max(lower, min(upper, val))
        return (val - lower) / (upper - lower)
    
    def _calculate_macro_alignment(
        self,
        ticker: str,
        direction: str,
        regime: str
    ) -> float:
        """Calculate how well ticker aligns with macro regime"""
        
        # Define asset classes
        GROWTH_STOCKS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA']
        DEFENSIVE_STOCKS = ['JNJ', 'PG', 'KO', 'WMT', 'PEP', 'MCD']
        SAFE_HAVENS = ['TLT', 'GLD', 'SHV', 'IEF']
        
        # Regime-specific alignment
        if regime == 'BULL_MARKET':
            if ticker in GROWTH_STOCKS and direction == 'up':
                return 1.0
            elif ticker in DEFENSIVE_STOCKS:
                return 0.3
        
        elif regime == 'BEAR_MARKET':
            if ticker in DEFENSIVE_STOCKS:
                return 0.9
            elif ticker in SAFE_HAVENS:
                return 1.0
            elif ticker in GROWTH_STOCKS:
                return 0.2
        
        elif regime == 'HIGH_VOLATILITY' or regime == 'RISK_OFF':
            if ticker in SAFE_HAVENS:
                return 1.0
            elif ticker in DEFENSIVE_STOCKS:
                return 0.7
            else:
                return 0.3
        
        elif regime == 'RISK_ON':
            if ticker in GROWTH_STOCKS and direction == 'up':
                return 0.9
        
        # Default: NORMAL regime
        return 0.5

    def _build_forecast_fusion(
        self,
        *,
        ticker: str,
        score: float,
        forecast: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Expose the deterministic multi-layer blend behind each recommendation."""
        direction = str(forecast.get("direction") or "flat").lower()
        expected_return = float(forecast.get("expected_return", 0.0) or 0.0)
        forecast_confidence = self._normalize(forecast.get("confidence"), 0.0, 1.0)
        expected_return_score = self._normalize(expected_return, -0.05, 0.05)
        news_context = forecast.get("market_context", {}) or {}
        news_sentiment = self._normalize(news_context.get("news_sentiment"), -0.6, 0.6)
        news_volume = self._normalize(news_context.get("news_volume_zscore"), -3.0, 3.0)
        macro_alignment = self._calculate_macro_alignment(
            ticker,
            direction,
            market_context.get("regime", "NORMAL"),
        )
        momentum = 0.8 if direction == "up" else 0.2 if direction == "down" else 0.5
        risk_reward = self._normalize(abs(expected_return), 0.0, 0.08)
        # Keep the layer list aligned with _calculate_ml_score so attribution stays auditable.
        layers = [
            {
                "layer": "forecast_confidence",
                "score": round(forecast_confidence, 3),
                "weight": 0.30,
                "contribution": round(forecast_confidence * 0.30, 3),
            },
            {
                "layer": "expected_return",
                "score": round(expected_return_score, 3),
                "weight": 0.20,
                "contribution": round(expected_return_score * 0.20, 3),
            },
            {
                "layer": "momentum",
                "score": round(momentum, 3),
                "weight": 0.20,
                "contribution": round(momentum * 0.20, 3),
            },
            {
                "layer": "news",
                "score": round((news_sentiment * 0.7) + (news_volume * 0.3), 3),
                "weight": 0.15,
                "contribution": round(((news_sentiment * 0.7) + (news_volume * 0.3)) * 0.15, 3),
            },
            {
                "layer": "macro_alignment",
                "score": round(macro_alignment, 3),
                "weight": 0.10,
                "contribution": round(macro_alignment * 0.10, 3),
            },
            {
                "layer": "risk_reward",
                "score": round(risk_reward, 3),
                "weight": 0.05,
                "contribution": round(risk_reward * 0.05, 3),
            },
        ]
        total_contribution = sum(max(float(item["contribution"]), 0.0) for item in layers)
        for item in layers:
            contribution = max(float(item["contribution"]), 0.0)
            normalized_contribution = (contribution / total_contribution) if total_contribution > 0 else 0.0
            item["normalized_contribution"] = round(normalized_contribution, 3)
            item["contribution_pct"] = round(normalized_contribution * 100, 1)

        ranked_layers = sorted(layers, key=lambda item: item["contribution"], reverse=True)
        dominant_layer = max(layers, key=lambda item: item["contribution"])
        runner_up_layer = ranked_layers[1] if len(ranked_layers) > 1 else dominant_layer
        dominance_gap = max(
            float(dominant_layer["normalized_contribution"]) - float(runner_up_layer["normalized_contribution"]),
            0.0,
        )
        if dominance_gap >= 0.15:
            stability = "stable"
        elif dominance_gap >= 0.05:
            stability = "watch"
        else:
            stability = "fragile"
        return {
            "blended_score": round(score, 3),
            "dominant_layer": dominant_layer["layer"],
            "layers": layers,
            "contribution_normalization": {
                "scheme": "layer_contribution_share",
                "sum": round(sum(float(item["normalized_contribution"]) for item in layers), 3),
            },
            "stability": {
                "status": stability,
                "dominance_gap": round(dominance_gap, 3),
                "dominant_share": dominant_layer["normalized_contribution"],
                "runner_up_layer": runner_up_layer["layer"],
                "runner_up_share": runner_up_layer["normalized_contribution"],
            },
            "attribution": {
                "forecast_direction": direction,
                "market_regime": market_context.get("regime", "NORMAL"),
                "expected_return": round(expected_return, 4),
                "news_sentiment": round(news_sentiment, 3),
                "macro_alignment": round(macro_alignment, 3),
            },
        }
    
    async def _validate_with_llm(
        self,
        ticker: str,
        score: float,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate recommendation with LLM"""
        
        if call_llm is None:
            return self._simulated_validation(ticker, score, data)
        
        try:
            prompt = self._build_validation_prompt(ticker, score, data)
            messages = [
                {
                    "role": "system",
                    "content": "Return ONLY valid JSON. No markdown, no prose.",
                },
                {"role": "user", "content": prompt},
            ]

            llm_res = call_llm(
                messages=messages,
                mode=os.getenv("LLM_RECOMMENDATIONS_MODE") or os.getenv("LLM_MODEL_MODE"),
                timeout=60,
                category_preference="forecast",
            )
            if not llm_res.get("ok"):
                raise RuntimeError(str(llm_res.get("error") or "llm_validation_failed"))
            content = str(llm_res.get("answer") or "")

            # Try to parse JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Extract from markdown code block if present
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    raise
            
        except Exception as e:
            self.logger.warning(f"LLM validation failed for {ticker}: {e}")
            return self._simulated_validation(ticker, score, data)
    
    def _build_validation_prompt(
        self,
        ticker: str,
        score: float,
        data: Dict[str, Any]
    ) -> str:
        """Build LLM validation prompt"""
        
        ticker_data = data.get(ticker, {})
        forecast = ticker_data.get('forecast', {})
        market_context = data.get('market_context', {})
        
        prompt = f"""You are a financial advisor analyzing market recommendations.

Current market regime: {market_context.get('regime', 'NORMAL')}
Market characteristics: {market_context.get('characteristics', {})}

Candidate recommendation:
- Ticker: {ticker}
- ML Score: {score:.2f}
- Forecast Direction: {forecast.get('direction', 'unknown')} (confidence: {forecast.get('confidence', 0)*100:.0f}%)
- Macro alignment: {"HIGH" if score > 0.7 else "MEDIUM" if score > 0.5 else "LOW"}

Task:
1. Validate this recommendation (APPROVE or REJECT)
2. If APPROVE, provide 2-3 sentence reasoning explaining why this is a good opportunity right now
3. Identify 2-3 key catalysts
4. Assess risk level (LOW, MEDIUM, or HIGH)

Output ONLY valid JSON with this structure:
{{
  "decision": "APPROVE" or "REJECT",
  "reasoning": "Your reasoning here (2-3 sentences)",
  "catalysts": ["catalyst1", "catalyst2", "catalyst3"],
  "risk_level": "LOW" or "MEDIUM" or "HIGH",
  "confidence": 0.0-1.0
}}"""
        
        return prompt
    
    def _simulated_validation(
        self,
        ticker: str,
        score: float,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulated validation when LLM unavailable"""
        
        ticker_data = data.get(ticker, {})
        forecast = ticker_data.get('forecast', {})
        direction = forecast.get('direction', 'flat')
        conf = forecast.get('confidence', 0.5)
        
        # Approve if score reasonably high
        if score < 0.5:
            return {
                'decision': 'REJECT',
                'reasoning': f"ML score ({score:.2f}) below threshold",
                'catalysts': [],
                'risk_level': 'HIGH',
                'confidence': 0.3
            }
        
        return {
            'decision': 'APPROVE',
            'reasoning': f"{ticker} shows {direction} momentum with {conf*100:.0f}% forecast confidence. Technical and fundamental alignment support this direction.",
            'catalysts': [
                f"Strong {direction} forecast signal",
                "Favorable macro environment",
                "Positive technical indicators"
            ],
            'risk_level': 'MEDIUM' if score > 0.75 else 'MEDIUM',
            'confidence': score
        }
    
    def _format_recommendations(
        self,
        validated: List[Dict],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format final recommendations output enriched with strategy playbooks (BATCH-15-DEV-02)"""

        recommendations = []

        # Get market regime for playbook resolution
        regime = market_context.get('regime', 'NORMAL')
        risk_profile = 'moderate'  # Default risk profile for recommendations

        for item in validated:
            ticker = item['ticker']
            score = item['score']
            forecast = item.get('data', {}).get('forecast', {})
            fusion = self._build_forecast_fusion(
                ticker=ticker,
                score=score,
                forecast=forecast,
                market_context=market_context,
            )

            rec = {
                'ticker': ticker,
                'action': 'BUY' if forecast.get('direction') == 'up' else 'HOLD',
                'score': round(score, 2),
                'reasoning': item.get('reasoning', 'No reasoning provided'),
                'catalysts': item.get('catalysts', []),
                'risk_level': item.get('risk_level', 'MEDIUM'),
                'confidence': round(item.get('confidence', score), 2),
                'supporting_data': {
                    'forecast_direction': forecast.get('direction', 'unknown'),
                    'forecast_confidence': round(forecast.get('confidence', 0.5), 2),
                    'ml_score': round(score, 2),
                    'forecast_fusion': fusion,
                },
                'forecast_fusion': fusion,
            }

            # Enrich with playbook context (BATCH-15-DEV-02)
            if self.playbook_resolver:
                # Map forecast direction to signal direction for playbook resolver
                forecast_dir = forecast.get('direction', 'flat')
                signal_direction_map = {
                    'up': 'bullish',
                    'down': 'bearish',
                    'flat': 'neutral'
                }
                signal_direction = signal_direction_map.get(forecast_dir.lower(), 'neutral')
                
                # Add signal direction and asset class for playbook enrichment
                rec['direction'] = signal_direction
                rec['asset_class'] = 'equities'  # Default to equities for stock recommendations

                # Use resolver's enrich method
                enriched = self.playbook_resolver.enrich_recommendation(
                    recommendation=rec,
                    regime=regime,
                    risk_profile=risk_profile,
                )
                rec = enriched

            recommendations.append(rec)

        return {
            'recommendations': recommendations,
            'market_context': {
                'regime': market_context.get('regime', 'NORMAL'),
                'summary': f"Market regime: {market_context.get('regime', 'NORMAL')}",
                'key_drivers': market_context.get('key_drivers', [])
            },
            'generated_at': datetime.utcnow().isoformat(),
            'valid_until': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
    
    def _fallback_recommendations(self) -> Dict[str, Any]:
        """Generate basic recommendations even when data is limited"""
        # Default universe for fallback
        default_tickers = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA']
        
        # Try to get basic market context
        try:
            from services.intelligence_service import get_market_intelligence_snapshot
            intel = get_market_intelligence_snapshot(use_cache=True, persist=False)
            regime = intel.get('insights', {}).get('market_regime', {}).get('current', 'NORMAL')
            summary = intel.get('insights', {}).get('summary', 'Market analysis in progress')
        except Exception:
            regime = 'NORMAL'
            summary = 'Market analysis in progress'
        
        # Generate basic recommendations based on default tickers
        recommendations = []
        for ticker in default_tickers[:3]:
            rec = {
                'ticker': ticker,
                'action': 'HOLD',
                'score': 0.5,
                'reasoning': f'{ticker} - Market analysis in progress. Monitor for entry signals.',
                'confidence': 0.5,
                'risk_level': 'MEDIUM',
                'catalysts': ['Market data collection ongoing'],
                'supporting_data': {
                    'forecast_confidence': 0.5,
                    'momentum_strength': 0.5,
                    'news_sentiment': 0.0,
                    'macro_alignment': 0.5
                }
            }
            if self.playbook_resolver:
                rec['direction'] = 'neutral'
                rec['asset_class'] = 'equities'
                rec = self.playbook_resolver.enrich_recommendation(
                    recommendation=rec,
                    regime=regime,
                    risk_profile='moderate',
                )
            recommendations.append(rec)
        
        return {
            'recommendations': recommendations,
            'market_context': {
                'regime': regime,
                'summary': summary,
                'key_drivers': ['Data collection in progress']
            },
            'generated_at': datetime.utcnow().isoformat(),
            'valid_until': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'status': 'fallback'
        }
    
    def _load_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Load from cache if valid"""
        try:
            cache_file = self.data_dir / f"{key}.json"
            if not cache_file.exists():
                return None
            
            data = json.loads(cache_file.read_text())
            
            # Check validity (24h)
            generated_at = datetime.fromisoformat(data.get('generated_at', '2000-01-01'))
            if datetime.utcnow() - generated_at > timedelta(hours=24):
                self.logger.info(f"Cache expired for {key}")
                return None

            if not data.get('recommendations'):
                # Don't reuse empty caches – force recompute
                return None
            
            return data
            
        except Exception as e:
            self.logger.warning(f"Cache load failed for {key}: {e}")
            return None
    
    def _save_cache(self, key: str, data: Dict[str, Any]):
        """Save to cache"""
        try:
            if not data.get('recommendations'):
                return
            cache_file = self.data_dir / f"{key}.json"
            cache_file.write_text(json.dumps(data, indent=2))
            self.logger.info(f"Saved cache for {key}")
        except Exception as e:
            self.logger.warning(f"Cache save failed for {key}: {e}")


# Singleton pattern
_recommendations_service_instance = None

def get_recommendations_service() -> RecommendationsService:
    """Get singleton instance of RecommendationsService"""
    global _recommendations_service_instance
    if _recommendations_service_instance is None:
        _recommendations_service_instance = RecommendationsService()
    return _recommendations_service_instance
