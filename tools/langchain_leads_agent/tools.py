"""
LangChain tools for a simple leads generation agent.
Implements:
 - search (DuckDuckGo)
 - scrape_website (search + first result scrape)
 - save (append structured text to a file)
"""
from __future__ import annotations

from datetime import datetime
from typing import List
import re

import requests
from bs4 import BeautifulSoup

try:
    from langchain_community.tools import DuckDuckGoSearchRun
    from langchain.tools import Tool
except Exception as e:  # pragma: no cover - optional dependency guard
    DuckDuckGoSearchRun = None  # type: ignore
    Tool = None  # type: ignore


def save_to_txt(data: str, filename: str = None) -> str:
    """Append human-readable data to a text file with a timestamp."""
    filename = filename or "tools/langchain_leads_agent/leads_output.txt"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"--- Leads Output ---\nTimestamp: {ts}\n\n{data}\n\n"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Data successfully saved to {filename}"


def scrape_website(url: str, limit: int = 5000) -> str:
    """Fetch raw text from a URL and squeeze whitespace; limit size."""
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:limit]
    except Exception as e:
        return f"Error scraping website: {e}"


def generate_search_queries(company_name: str) -> List[str]:
    kws = ["IT Services", "managed IT", "technology solutions"]
    return [f"{company_name} {kw}" for kw in kws]


def _extract_urls(search_output: str) -> List[str]:
    pat = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    return re.findall(pat, search_output or "")


def search_and_scrape(company_name: str) -> str:
    """Search with DDG, then scrape the first URL for each query and concat."""
    if DuckDuckGoSearchRun is None:
        return "DuckDuckGoSearchRun not available. Please install langchain-community."
    search = DuckDuckGoSearchRun()
    results: List[str] = []
    for q in generate_search_queries(company_name):
        try:
            out = search.run(q)
            urls = _extract_urls(out)
            if urls:
                results.append(scrape_website(urls[0]))
        except Exception:
            continue
    return " ".join(results)


def make_langchain_tools():
    """Return LangChain Tool instances (requires langchain installed)."""
    if Tool is None or DuckDuckGoSearchRun is None:
        raise RuntimeError("LangChain tools unavailable. Install langchain & langchain-community.")

    ddg = DuckDuckGoSearchRun()
    search_tool = Tool(
        name="search",
        func=ddg.run,
        description="Search the web for information via DuckDuckGo.",
    )

    scrape_tool = Tool(
        name="scrape_website",
        func=search_and_scrape,
        description="Search + scrape text for a given company name.",
    )

    save_tool = Tool(
        name="save",
        func=save_to_txt,
        description="Append structured text to a file.",
    )

    return search_tool, scrape_tool, save_tool

