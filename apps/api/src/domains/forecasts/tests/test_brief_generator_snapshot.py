from services import brief_generator


def test_build_daily_brief_snapshot_wraps_brief_in_canonical_daily_shape():
    brief = {
        "summary": "Ouverture constructive.",
        "headline": "Brief Marche",
        "freshness": "2026-03-13T10:00:00Z",
        "generated_at": "2026-03-13T10:00:00Z",
        "source": ["brief_generator", "live_data"],
        "sources": ["brief_generator", "live_data"],
        "warnings": [],
        "degraded": False,
        "degraded_reason": None,
        "generation_metadata": {
            "schedule_mode": "refreshable_script",
            "artifact_key": "brief_daily",
            "artifact_path": "runtime/data/brief_daily.json",
            "refreshed_at": "2026-03-13T10:00:00Z",
        },
    }

    payload = brief_generator.build_daily_brief_snapshot(brief)

    assert payload["data"]["daily"]["summary"] == "Ouverture constructive."
    assert payload["data"]["daily"]["generation_metadata"]["artifact_key"] == "brief_daily"
    assert payload["generation_metadata"]["artifact_path"] == "runtime/data/brief_daily.json"
    assert payload["freshness"] == "2026-03-13T10:00:00Z"
