from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application.judge_pipeline import parse_llm_answer


def _fixture_payload():
    return {
        "summary": ["Signal clair sur la tendance globale."],
        "scenarios": [{"name": "base", "impact": "neutre"}],
        "risks": ["Risque de volatilité."],
        "impacts": {"upside": 1.2, "downside": 0.8},
        "actions": ["Conserver", "Surveiller vol"],
        "confidence": 0.74,
    }


def test_parse_llm_answer_reads_markdown_fenced_json():
    payload = _fixture_payload()
    raw = (
        "Analyse quick:\n"
        "```json\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n```\n"
        "Confiance modérée."
    )
    parsed = parse_llm_answer(raw)
    assert parsed["summary"] == payload["summary"]
    assert parsed["confidence"] == payload["confidence"]


def test_parse_llm_answer_reads_embedded_json_with_trailing_text():
    payload = _fixture_payload()
    raw = f'Prefixe: {json.dumps(payload, ensure_ascii=False)} done.'
    parsed = parse_llm_answer(raw)
    assert parsed["scenarios"] == payload["scenarios"]
    assert parsed["risks"] == payload["risks"]


def test_parse_llm_answer_fallback_when_missing_required_json_keys():
    raw = "Here is a response with {'message': 'partial'} but no required keys."
    parsed = parse_llm_answer(raw)
    assert parsed["error"] == "json_parse_failed"
    assert parsed["summary"] == [raw]
