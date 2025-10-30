LangChain Leads Agent (Gemini)

Overview
- A minimal AI agent (LangChain) that searches the web for potential leads, scrapes basic info, and generates a structured list with an outreach message.
- Implements three tools: `search`, `scrape_website` (search+scrape combo), and `save` (append output to a text file).
- Default model: Google Gemini 2.5 Flash via `langchain-google-genai`.

Quickstart
1) Env var
- Create a `.env` file at repo root or in this folder with:
  - `GEMINI_API_KEY="YOUR_API_KEY"`

2) Install deps
- The repo `requirements.txt` includes the needed packages. From your virtualenv:
- `pip install -r requirements.txt`

3) Run
- `PYTHONPATH=src python tools/langchain_leads_agent/main.py`  
  Options:
  - `--city "Vancouver"` (default)
  - `--service "IT services"` (default)
  - `--count 5` (default)

Outputs
- Appends a time‑stamped section to `tools/langchain_leads_agent/leads_output.txt`.

Notes
- The implementation is defensive: if a package is missing or the API key is absent, a clear message is printed and the process exits gracefully.
- You can swap the model provider by replacing `langchain-google-genai` with `langchain-openai`, `langchain-anthropic`, or `langchain-groq` and adjusting the API keys.

