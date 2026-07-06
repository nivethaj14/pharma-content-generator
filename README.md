# PharmaContent — GenAI Content Generator for Medical Affairs

🔗 **Live Demo**: https://pharma-content-generator.streamlit.app

A GenAI-powered content generation platform for medical affairs teams,
built on Snowflake Cortex and Model Context Protocol (MCP).
Part of a 3-project pharma AI portfolio.

---

## Problem Statement

Medical affairs teams spend significant time manually creating plain
language summaries, competitive intelligence briefs, and regulatory
context documents. PharmaContent automates this using GenAI with a
human review loop and full audit trail — critical for pharma compliance.

---

## Architecture
Clinical Trial Data (Snowflake)     FDA FAERS Signals (Snowflake)
FDA Guidance Docs (Cortex Search)
↓
MCP Server
(6 standardized tools)
↓
Content Generator
(Snowflake Cortex LLM)
↓
Human Review Loop
(edit, approve, reject)
↓
Audit Trail (Snowflake)
(version, model, status)
---

## MCP Tools

| Tool | Purpose |
|------|---------|
| `get_trial_summary` | Fetch clinical trial data by condition/phase |
| `get_safety_signals` | Get FAERS safety signals for a drug |
| `get_regulatory_context` | Search FDA guidance documents |
| `generate_plain_language_summary` | Generate summaries for patient/HCP/regulator |
| `generate_competitive_brief` | Generate competitive intelligence brief |
| `save_content_version` | Save to audit trail with versioning |

---

## Tech Stack

- **MCP (Model Context Protocol)** — standardized tool interface
- **Snowflake Cortex COMPLETE** — Mistral Large 2 for generation
- **Snowflake Cortex Search** — FDA document retrieval (Project 1)
- **Snowflake SQL** — clinical trial and FAERS data queries
- **Python 3.11** — MCP server and content generation
- **Streamlit 1.58** — 4-tab content generation UI

---

## Features

- **4 content types** — plain language summaries (3 audiences),
  competitive briefs, regulatory summaries
- **3 target audiences** — patient, HCP, regulatory reviewer
- **Human review loop** — edit before approving and saving
- **Audit trail** — every document versioned with model, prompt
  version, status, timestamps
- **MCP architecture** — standardized tool protocol for enterprise
  AI integration
- **Cross-project data reuse** — uses trial data from Project 2
  and FDA documents from Project 1

---

## Local Setup

```bash
git clone https://github.com/nivethaj14/pharma-content-generator.git
cd pharma-content-generator
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Snowflake credentials
streamlit run app.py
```

---

## Project Structure
pharma-content-generator/
├── app.py                      # Streamlit 4-tab UI
├── src/
│   ├── mcp_server.py           # MCP server with 6 tools
│   └── test_mcp.py             # MCP tool tests
├── docs/
├── requirements.txt
└── README.md
---

## Author

Built by a pharma AI practitioner with 12 years of life sciences
experience. Part of a 3-project GenAI/Agentic AI portfolio.

---

## License

MIT License