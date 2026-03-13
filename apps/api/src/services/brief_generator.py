"""
Daily Brief Generator Service
Generates market brief from live data: macro signals, sector rotation, summary

Architecture:
- Reuses existing forecast, judge, and monitor sources
- Explicit degradation metadata when sources are unavailable
- Freshness tracking for scheduled generation validation
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Import live data services
try:
    from services.forecasts_service import get_forecasts_from_storage
    from services.news_service import get_news_feed
    from services.macro_service import get_macro_indicators
except ImportError:
    get_forecasts_from_storage = None
    get_news_feed = None
    get_macro_indicators = None


def _utc_now_iso() -> str:
    """Return current UTC time in ISO format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_daily_brief_snapshot(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap the generated brief in the canonical `data.daily` artifact shape."""
    payload = dict(brief or {})
    generated_at = str(payload.get("generated_at") or _utc_now_iso()).strip() or _utc_now_iso()
    freshness = str(payload.get("freshness") or generated_at).strip() or generated_at
    generation_metadata = payload.get("generation_metadata")
    if not isinstance(generation_metadata, dict):
        generation_metadata = {}
    generation_metadata.setdefault("artifact_key", "brief_daily")
    generation_metadata.setdefault("artifact_path", "runtime/data/brief_daily.json")
    generation_metadata.setdefault("freshness", freshness)
    generation_metadata.setdefault("refreshed_at", generated_at)
    payload["generated_at"] = generated_at
    payload["freshness"] = freshness
    payload["generation_metadata"] = generation_metadata
    return {
        "data": {"daily": payload},
        "generated_at": generated_at,
        "freshness": freshness,
        "source": list(payload.get("source") or payload.get("sources") or ["brief_generator"]),
        "warnings": list(payload.get("warnings") or []),
        "degraded": bool(payload.get("degraded")),
        "degraded_reason": payload.get("degraded_reason"),
        "generation_metadata": dict(generation_metadata),
    }


def _generate_market_summary(forecasts: List[Dict], news: List[Dict], macro: Dict) -> str:
    """Generate a concise market summary (< 200 words) from live data."""
    summary_parts = []
    
    # Analyze forecast sentiment
    if forecasts:
        bullish = sum(1 for f in forecasts if f.get('direction') == 'up' and f.get('confidence', 0) > 0.5)
        bearish = sum(1 for f in forecasts if f.get('direction') == 'down' and f.get('confidence', 0) > 0.5)
        total_confident = bullish + bearish
        
        if total_confident > 0:
            sentiment_ratio = bullish / total_confident
            if sentiment_ratio > 0.6:
                summary_parts.append("Les forecasts IA sont majoritairement haussiers avec une confiance élevée.")
            elif sentiment_ratio < 0.4:
                summary_parts.append("Les forecasts IA penchent vers la prudence avec des signaux baissiers.")
            else:
                summary_parts.append("Les forecasts IA montrent un marché mitigé sans direction claire.")
    
    # Add macro context
    if macro and macro.get('indicators'):
        indicators = macro['indicators']
        if indicators.get('vix'):
            vix = indicators['vix']
            if vix > 20:
                summary_parts.append("Le VIX élevé signale une volatilité accrue sur les marchés.")
            elif vix < 15:
                summary_parts.append("Le VIX bas indique un marché calme et confiant.")
        
        if indicators.get('dxy'):
            dxy = indicators['dxy']
            if dxy > 105:
                summary_parts.append("Le dollar fort pèse sur les marchés émergents.")
            elif dxy < 100:
                summary_parts.append("Le dollar faible soutient les actifs à risque.")
    
    # Add news sentiment
    if news:
        positive_news = sum(1 for n in news if n.get('sentiment') == 'positive')
        negative_news = sum(1 for n in news if n.get('sentiment') == 'negative')
        if positive_news > negative_news * 1.5:
            summary_parts.append("Les news récentes sont majoritairement positives.")
        elif negative_news > positive_news * 1.5:
            summary_parts.append("Les news récentes signalent des risques à surveiller.")
    
    if not summary_parts:
        summary_parts.append("Le marché reste actif avec une lecture mitigée. Surveillez les secteurs en rotation.")
    
    return " ".join(summary_parts)


def _compute_sector_rotation(forecasts: List[Dict]) -> Dict[str, List[str]]:
    """Compute top and bottom sectors from forecasts."""
    sector_map = {
        'NVDA': 'IA', 'MSFT': 'IA', 'GOOGL': 'IA', 'META': 'IA', 'AAPL': 'Tech',
        'TSLA': 'EV', 'SPY': 'US Large Cap', 'QQQ': 'Tech',
        'GLD': 'Or', 'SLV': 'Argent', 'XLE': 'Énergie', 'BTC': 'Crypto'
    }
    
    sector_scores: Dict[str, List[float]] = {}
    
    for forecast in forecasts:
        ticker = forecast.get('ticker', '')
        sector = sector_map.get(ticker, 'Autre')
        confidence = forecast.get('confidence', 0.5)
        direction = forecast.get('direction', 'flat')
        
        score = confidence if direction == 'up' else -confidence
        
        if sector not in sector_scores:
            sector_scores[sector] = []
        sector_scores[sector].append(score)
    
    # Average scores per sector
    sector_avg = {sector: sum(scores) / len(scores) for sector, scores in sector_scores.items()}
    
    # Sort and get top 3 / bottom 3
    sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
    
    top = [s[0] for s in sorted_sectors[:3] if s[1] > 0]
    bottom = [s[0] for s in sorted_sectors[-3:] if s[1] < 0]
    
    return {'top': top, 'bottom': bottom}


def _get_macro_signals() -> List[Dict[str, Any]]:
    """Get macro signals from service or fallback."""
    if get_macro_indicators:
        try:
            macro = get_macro_indicators()
            if macro and macro.get('indicators'):
                signals = []
                indicators = macro['indicators']
                
                if indicators.get('vix'):
                    vix = indicators['vix']
                    signals.append({
                        'name': 'VIX',
                        'value': str(vix),
                        'signal': 'risk_off' if vix > 20 else 'risk_on',
                        'impact': 'high'
                    })
                
                if indicators.get('dxy'):
                    dxy = indicators['dxy']
                    signals.append({
                        'name': 'DXY',
                        'value': str(dxy),
                        'signal': 'dollar_strong' if dxy > 105 else 'dollar_weak',
                        'impact': 'medium'
                    })
                
                if indicators.get('fed_rate'):
                    signals.append({
                        'name': 'Fed Rate',
                        'value': str(indicators['fed_rate']) + '%',
                        'signal': 'hawkish' if indicators['fed_rate'] > 5 else 'dovish',
                        'impact': 'high'
                    })
                
                return signals
        except Exception as e:
            logger.warning(f"Error getting macro indicators: {e}")
    
    # Fallback
    return [
        {'name': 'VIX', 'value': '14.5', 'signal': 'risk_on', 'impact': 'medium'},
        {'name': 'DXY', 'value': '103.2', 'signal': 'neutral', 'impact': 'low'}
    ]


def generate_daily_brief() -> Dict[str, Any]:
    """
    Generate a complete daily brief from live data.

    Returns:
        Dict containing summary, macro_signals, sector_rotation, etc.
        with explicit freshness and degradation metadata.
    """
    warnings: List[str] = []
    degraded_reasons: List[str] = []
    source_tags = ["brief_generator", "live_data"]

    # Fetch live data with explicit error tracking
    forecasts = []
    news = []
    macro = {}

    if get_forecasts_from_storage:
        try:
            result = get_forecasts_from_storage(limit=50)
            forecasts = result.get('rows', []) if isinstance(result, dict) else []
            if not forecasts:
                warnings.append("forecasts_empty")
        except Exception as e:
            logger.warning(f"Error loading forecasts: {e}")
            warnings.append("forecasts_unavailable")
            degraded_reasons.append("forecasts_failed")
    else:
        warnings.append("forecasts_service_unavailable")
        degraded_reasons.append("forecasts_not_installed")

    if get_news_feed:
        try:
            result = get_news_feed(limit=50)
            news = result.get('articles', []) if isinstance(result, dict) else []
            if not news:
                warnings.append("news_empty")
        except Exception as e:
            logger.warning(f"Error loading news: {e}")
            warnings.append("news_unavailable")
            degraded_reasons.append("news_failed")
    else:
        warnings.append("news_service_unavailable")
        degraded_reasons.append("news_not_installed")

    if get_macro_indicators:
        try:
            macro = get_macro_indicators()
            if not macro or not macro.get('indicators'):
                warnings.append("macro_empty")
        except Exception as e:
            logger.warning(f"Error loading macro: {e}")
            warnings.append("macro_unavailable")
            degraded_reasons.append("macro_failed")
    else:
        warnings.append("macro_service_unavailable")
        degraded_reasons.append("macro_not_installed")

    # Determine degradation state
    is_degraded = len(degraded_reasons) >= 2 or (len(degraded_reasons) == 1 and len(warnings) >= 2)
    degradation_reason = ",".join(degraded_reasons) if degraded_reasons else None

    # Generate summary (may be degraded)
    summary = _generate_market_summary(forecasts, news, macro)
    if is_degraded and "degraded" not in summary.lower():
        summary = "[Mode dégradé] " + summary

    # Truncate to < 200 words
    words = summary.split()
    if len(words) > 200:
        summary = " ".join(words[:200])

    # Compute sector rotation
    sector_rotation = _compute_sector_rotation(forecasts)

    # Get macro signals
    macro_signals = _get_macro_signals()

    # Determine market sentiment
    sentiment = 'neutral'
    if forecasts:
        bullish = sum(1 for f in forecasts if f.get('direction') == 'up' and f.get('confidence', 0) > 0.5)
        bearish = sum(1 for f in forecasts if f.get('direction') == 'down' and f.get('confidence', 0) > 0.5)
        if bullish > bearish * 1.3:
            sentiment = 'bullish'
        elif bearish > bullish * 1.3:
            sentiment = 'bearish'

    generated_at = _utc_now_iso()

    brief = {
        'summary': summary,
        'headline': f"Brief Marché - {datetime.now().strftime('%d/%m/%Y')}",
        'sentiment': sentiment,
        'macro_signals': macro_signals,
        'sector_rotation': sector_rotation,
        'top_signals': [],
        'top_risks': [],
        'key_events': [],
        'generated_at': generated_at,
        'freshness': generated_at,
        'source': source_tags,
        'sources': source_tags,
        'warnings': warnings,
        'degraded': is_degraded,
        'degraded_reason': degradation_reason,
        'generation_metadata': {
            'schedule_mode': 'refreshable_script',
            'target_local_time': os.getenv('MORNING_BRIEF_TARGET_HOUR_LOCAL', '06:30'),
            'target_timezone': os.getenv('MORNING_BRIEF_TIMEZONE', os.getenv('TZ', 'America/New_York')),
            'artifact_key': 'brief_daily',
            'artifact_path': 'runtime/data/brief_daily.json',
            'refreshed_at': generated_at,
            'data_quality': {
                'forecasts_count': len(forecasts),
                'news_count': len(news),
                'macro_indicators': len(macro.get('indicators', {})) if macro else 0,
            }
        }
    }

    return brief


def save_daily_brief() -> Optional[Dict[str, Any]]:
    """Generate and save daily brief to storage with explicit degradation tracking."""
    from storage.io import save_json

    try:
        brief = generate_daily_brief()
        snapshot = build_daily_brief_snapshot(brief)
        filepath = save_json('brief_daily', snapshot, source=['brief_generator'])
        if filepath:
            logger.info(f"Daily brief saved to {filepath}")
            logger.info(f"Degraded: {brief.get('degraded', False)}, Warnings: {brief.get('warnings', [])}")
            return brief
        else:
            logger.error("Failed to save daily brief")
            return None
    except Exception as e:
        logger.error(f"Error saving daily brief: {e}")
        # Return explicit degraded fallback
        fallback = _fallback_degraded_brief(error=str(e))
        try:
            save_json(
                'brief_daily',
                build_daily_brief_snapshot(fallback),
                source=['brief_generator', 'critical_fallback'],
            )
        except Exception:
            pass
        return fallback


def _fallback_degraded_brief(*, error: str) -> Dict[str, Any]:
    """Return explicit degraded brief when generation fails completely."""
    generated_at = _utc_now_iso()
    return {
        'summary': f"[Mode dégradé] Le brief automatique n'a pas pu être généré. Erreur: {error}",
        'headline': f"Brief Marché - {datetime.now().strftime('%d/%m/%Y')} (dégradé)",
        'sentiment': 'unknown',
        'macro_signals': [],
        'sector_rotation': {'top': [], 'bottom': []},
        'top_signals': [],
        'top_risks': [],
        'key_events': [],
        'generated_at': generated_at,
        'freshness': generated_at,
        'source': ['brief_generator', 'critical_fallback'],
        'sources': ['brief_generator', 'critical_fallback'],
        'warnings': ['generation_failed'],
        'degraded': True,
        'degraded_reason': f'generation_exception: {error}',
        'generation_metadata': {
            'schedule_mode': 'fallback',
            'target_local_time': os.getenv('MORNING_BRIEF_TARGET_HOUR_LOCAL', '06:30'),
            'target_timezone': os.getenv('MORNING_BRIEF_TIMEZONE', os.getenv('TZ', 'America/New_York')),
            'artifact_key': 'brief_daily',
            'artifact_path': 'runtime/data/brief_daily.json',
            'refreshed_at': generated_at,
            'error': error,
        }
    }


if __name__ == '__main__':
    # CLI usage: python -m services.brief_generator
    import json
    brief = generate_daily_brief()
    print(json.dumps(brief, indent=2, ensure_ascii=False))
