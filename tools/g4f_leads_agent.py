"""
G4F Leads Agent — simple lead generation via web search + scrape + g4f LLM

Usage:
  PYTHONPATH=src python tools/g4f_leads_agent.py --city "Vancouver" --service "IT services" --count 5

Notes:
  - Relies on duckduckgo_search for quick web queries.
  - Scrapes first pages' text, then asks a powerful no‑auth g4f model to synthesize
    exactly N leads with fields: company, contact_info, email, summary, outreach_message.
  - Appends a time‑stamped block to tools/langchain_leads_agent/leads_output.txt
    (reuses save_to_txt from tools/langchain_leads_agent/tools.py).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Dict

from duckduckgo_search import DDGS

try:
    from g4f.client import Client as G4FClient
except Exception as e:
    raise RuntimeError("g4f non installé. Fais `pip install -U g4f` dans ton venv.") from e

try:
    # Reuse save/scrape helpers we added
    from tools.langchain_leads_agent.tools import save_to_txt, scrape_website
except Exception:  # fallback if import path differs
    from tools.langchain_leads_agent import tools as _t  # type: ignore
    save_to_txt = _t.save_to_txt
    scrape_website = _t.scrape_website


# Powerful no‑auth defaults (see src/analytics/econ_llm_agent.py for more)
DEFAULT_MODEL = os.getenv(
    "G4F_LEADS_MODEL",
    "deepseek-ai/DeepSeek-R1-0528",
)


@dataclass
class CandidateSite:
    title: str
    url: str
    text: str


def search_local_sites(city: str, service: str, max_results: int = 10) -> List[CandidateSite]:
    """Search DuckDuckGo for local small businesses potentially matching the service.
    Returns a list of candidate sites with basic scraped text (limited).
    """
    q = f"{service} small business {city}"
    items: List[CandidateSite] = []
    seen = set()
    with DDGS() as ddg:
        for r in ddg.text(q, max_results=max_results):
            url = r.get("href") or r.get("url") or ""
            title = r.get("title") or r.get("body") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            txt = scrape_website(url)
            items.append(CandidateSite(title=title, url=url, text=txt))
            # small pause to be polite
            time.sleep(0.2)
            if len(items) >= max_results:
                break
    return items


def build_prompt(city: str, service: str, count: int, sites: List[CandidateSite]) -> str:
    # We give compact attachments to the model
    atts = [
        {
            "title": s.title,
            "url": s.url,
            "text": (s.text or "")[:4000],
        }
        for s in sites[: max(5, count * 2)]
    ]
    return (
        "You are a sales enablement assistant.\n"
        f"Goal: Find exactly {count} local small businesses in {city} that could need {service}.\n"
        "Use the attachments (webpage texts) as factual context.\n"
        "Return a JSON with key 'leads' = list of objects with: company, contact_info, email, summary, outreach_message, tools_used.\n"
        "- company: inferred from page\n"
        "- contact_info: addresses/phones if present\n"
        "- email: extract if present, else empty string\n"
        "- summary: short qualification for IT needs\n"
        "- outreach_message: short friendly message\n"
        "- tools_used: ['duckduckgo','scrape']\n"
        "Output strictly one JSON object with the 'leads' array (length exactly the requested count).\n"
        f"ATTACHMENTS_JSON={json.dumps(atts, ensure_ascii=False)}\n"
    )


def call_g4f(model: str, prompt: str) -> str:
    client = G4FClient()
    msgs = [
        {"role": "system", "content": "You are a helpful assistant. Do not reveal hidden reasoning."},
        {"role": "user", "content": prompt},
    ]
    res = client.chat.completions.create(
        model=model,
        messages=msgs,
        temperature=float(os.getenv("G4F_LEADS_TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("G4F_LEADS_MAX_TOKENS", "1500")),
    )
    try:
        return (res.choices[0].message.content or "").strip()
    except Exception:
        return str(res)


def parse_json_only(text: str) -> Dict:
    text = (text or "").strip()
    # If the model returns extra text, try to extract the first JSON block
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass
    # Fallback: try directly
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def main():
    ap = argparse.ArgumentParser(description="G4F leads agent")
    ap.add_argument("--city", default="Vancouver")
    ap.add_argument("--service", default="IT services")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    sites = search_local_sites(args.city, args.service, max_results=max(5, args.count * 3))
    if not sites:
        print("Aucun résultat web. Essayez un autre service/ville.")
        sys.exit(1)

    prompt = build_prompt(args.city, args.service, args.count, sites)
    raw = call_g4f(args.model, prompt)
    data = parse_json_only(raw)

    # Pretty print and save
    try:
        print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
    except Exception:
        print(str(data)[:2000])
    try:
        save_to_txt(json.dumps(data, ensure_ascii=False))
        print("(saved to tools/langchain_leads_agent/leads_output.txt)")
    except Exception as e:
        print("Save failed:", e)


if __name__ == "__main__":
    main()

