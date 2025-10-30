"""
LangChain leads agent (Gemini 2.5 Flash)

Usage:
  PYTHONPATH=src python tools/langchain_leads_agent/main.py --city "Vancouver" --service "IT services" --count 5

Notes:
- Requires environment variable GEMINI_API_KEY set (e.g., via a .env file).
- Dependencies are listed in the project requirements.txt (langchain, langchain-community, langchain-google-genai, duckduckgo-search, pydantic, python-dotenv, beautifulsoup4).
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from pydantic import BaseModel


def _missing(msg: str):
    print(msg)
    sys.exit(1)


def _import_langchain():
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain.agents import create_tool_calling_agent, AgentExecutor
        return ChatGoogleGenerativeAI, ChatPromptTemplate, PydanticOutputParser, create_tool_calling_agent, AgentExecutor
    except Exception:
        _missing(
            "LangChain Google GenAI not installed. Please run: pip install langchain langchain-community langchain-google-genai duckduckgo-search pydantic python-dotenv beautifulsoup4"
        )


try:
    from tools.langchain_leads_agent.tools import make_langchain_tools
except Exception:
    # local import fallback when running from folder
    from tools import make_langchain_tools  # type: ignore


class LeadResponse(BaseModel):
    company: str
    contact_info: str
    email: str
    summary: str
    outreach_message: str
    tools_used: list[str]


class LeadResponseList(BaseModel):
    leads: list[LeadResponse]


def build_agent(city: str, service: str, count: int):
    ChatGoogleGenerativeAI, ChatPromptTemplate, PydanticOutputParser, create_tool_calling_agent, AgentExecutor = _import_langchain()

    # Ensure API key
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        _missing("Missing GEMINI_API_KEY in environment. Create a .env with GEMINI_API_KEY=... or export it.")

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    parser = PydanticOutputParser(pydantic_object=LeadResponseList)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a sales enablement assistant.
                1. Use the 'scrape_website' tool to find exactly {count} local small businesses in {city}, from varied industries, that might need {service}.
                2. For each company found, use the 'search' tool to enrich details.
                3. For each lead, return:
                   - company, contact_info, email, summary, outreach_message, tools_used
                4. Format output using: {format_instructions}
                5. After formatting, call the 'save' tool to append the JSON to a file.
                6. Finally, add one sentence stating whether the 'save' tool was executed.
                """,
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions(), city=city, service=service, count=count)

    # LangChain Tool instances
    search_tool, scrape_tool, save_tool = make_langchain_tools()
    tools = [scrape_tool, search_tool, save_tool]

    agent = create_tool_calling_agent(
        llm=llm,
        prompt=prompt,
        tools=tools,
    )

    return AgentExecutor(agent=agent, tools=tools, verbose=True), parser


def main():
    ap = argparse.ArgumentParser(description="LangChain leads agent (Gemini)")
    ap.add_argument("--city", default="Vancouver")
    ap.add_argument("--service", default="IT services")
    ap.add_argument("--count", type=int, default=5)
    args = ap.parse_args()

    agent_executor, parser = build_agent(args.city, args.service, args.count)
    query = f"Find and qualify exactly {args.count} local leads in {args.city} for {args.service}. No more than {args.count} small businesses."
    raw = agent_executor.invoke({"query": query})

    try:
        out = raw.get("output") if isinstance(raw, dict) else None
        if out is None:
            print("No structured output; full raw:", raw)
            return
        structured = parser.parse(out)
        print(structured)
    except Exception as e:
        print("Error parsing response:", e)
        print("Raw:", raw)


if __name__ == "__main__":
    main()

