#!/usr/bin/env python3
"""
Generate the canonical daily brief artifact for `/api/brief/daily`.

BATCH-25-DEV-01: Minimal scheduled generation slice
- Produces durable artifact at runtime/data/brief_daily.json
- Explicit freshness/degraded metadata in generation_metadata
- Fallback to degraded brief on complete failure
"""
import sys
import os
from datetime import datetime, timezone
from pathlib import Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_generation_metadata(*, script_path: str, artifact_key: str) -> dict:
    target_hour = os.getenv("MORNING_BRIEF_TARGET_HOUR_LOCAL", "06:30").strip() or "06:30"
    timezone_name = os.getenv("MORNING_BRIEF_TIMEZONE", os.getenv("TZ", "America/New_York")).strip() or "America/New_York"
    return {
        "schedule_mode": "refreshable_script",
        "target_local_time": target_hour,
        "target_timezone": timezone_name,
        "artifact_key": artifact_key,
        "artifact_path": f"runtime/data/{artifact_key}.json",
        "refreshed_by": script_path,
        "refreshed_at": _utc_now_iso(),
    }


def _with_generation_metadata(brief: dict, *, script_path: str, artifact_key: str = "brief_daily") -> dict:
    payload = dict(brief or {})
    payload["generation_metadata"] = _build_generation_metadata(
        script_path=script_path,
        artifact_key=artifact_key,
    )
    return payload

# Add backend src to path
backend_root = os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', 'src')
backend_root = os.path.abspath(backend_root)
if os.path.exists(backend_root):
    sys.path.insert(0, backend_root)
    print(f"Added to path: {backend_root}")

# Set PYTHONPATH for imports
os.environ['PYTHONPATH'] = backend_root

try:
    from services.brief_generator import save_daily_brief, build_daily_brief_snapshot
    from storage import io as storage_io
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Backend root: {backend_root}")
    print(f"Path exists: {os.path.exists(backend_root)}")
    import json

    script_ref = os.path.relpath(__file__, start=os.path.dirname(__file__))

    # Explicit degraded fallback when service unavailable
    brief = {
        'summary': "[Mode dégradé] Le générateur de brief n'est pas disponible. Les services de données ne sont pas installés.",
        'headline': f"Brief Marché - {datetime.now().strftime('%d/%m/%Y')} (dégradé)",
        'sentiment': 'unknown',
        'macro_signals': [
            {'name': 'VIX', 'value': 'N/A', 'signal': 'unknown', 'impact': 'unknown'},
            {'name': 'DXY', 'value': 'N/A', 'signal': 'unknown', 'impact': 'unknown'}
        ],
        'sector_rotation': {'top': [], 'bottom': []},
        'top_signals': [],
        'top_risks': [],
        'key_events': [],
        'generated_at': _utc_now_iso(),
        'freshness': _utc_now_iso(),
        'source': ['brief_generator', 'fallback_degraded'],
        'sources': ['brief_generator', 'fallback_degraded'],
        'warnings': ['services_unavailable', 'using_static_fallback'],
        'degraded': True,
        'degraded_reason': 'brief_generator_service_not_installed',
    }

    brief = _with_generation_metadata(brief, script_path=script_ref)
    snapshot = {
        "data": {"daily": brief},
        "generated_at": brief["generated_at"],
        "freshness": brief["freshness"],
        "source": list(brief.get("source") or []),
        "warnings": list(brief.get("warnings") or []),
        "degraded": True,
        "degraded_reason": brief.get("degraded_reason"),
        "generation_metadata": dict(brief.get("generation_metadata") or {}),
    }

    runtime_data_dir = Path(backend_root).parent / "runtime" / "data"
    runtime_data_dir.mkdir(parents=True, exist_ok=True)
    filepath = runtime_data_dir / "brief_daily.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"✅ Brief saved to {filepath}")
    print(f"\nSummary:")
    print(brief['summary'])
    sys.exit(0)

if __name__ == '__main__':
    print("Generating daily brief...")
    script_ref = os.path.relpath(__file__, start=os.path.dirname(__file__))
    brief = save_daily_brief()

    if brief:
        snapshot = storage_io.load_json("brief_daily") or {}
        persisted_payload = snapshot.get("data") if isinstance(snapshot.get("data"), dict) else snapshot
        if isinstance(persisted_payload, dict) and isinstance(persisted_payload.get("daily"), dict):
            persisted_payload = persisted_payload.get("daily")
        enriched_brief = _with_generation_metadata(
            dict(persisted_payload or brief),
            script_path=script_ref,
        )
        storage_io.save_json(
            "brief_daily",
            build_daily_brief_snapshot(enriched_brief),
            source=["brief_generator", "scheduled_refresh"],
        )
        
        # Evidence output for planner verification
        print("✅ Daily brief generated and saved successfully!")
        print(f"\n--- Generation Evidence ---")
        print(f"Artifact: runtime/data/brief_daily.json")
        print(f"Degraded: {brief.get('degraded', False)}")
        print(f"Warnings: {brief.get('warnings', [])}")
        print(f"Freshness: {brief.get('freshness', 'N/A')}")
        print(f"Summary ({len(brief['summary'].split())} words):")
        print(brief['summary'][:200] + "..." if len(brief['summary']) > 200 else brief['summary'])
        print(f"\nSector Rotation - Top: {brief['sector_rotation']['top']}")
        print(f"Sector Rotation - Bottom: {brief['sector_rotation']['bottom']}")
        print(f"\nMacro Signals: {len(brief['macro_signals'])} indicators")
        print(f"Sentiment: {brief['sentiment']}")
        
        # Exit with degraded warning if applicable
        if brief.get('degraded'):
            print(f"\n⚠️  BRIEF DEGRADED: {brief.get('degraded_reason')}")
            sys.exit(0)  # Still success - degraded brief is valid output
    else:
        print("❌ Failed to generate daily brief")
        sys.exit(1)
