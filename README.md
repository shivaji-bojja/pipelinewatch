# PipelineWatch

A multi-agent system that scores CRM pipeline deals for risk and produces
a plain-English executive summary — built for the Kaggle AI Agents
Intensive Vibe Coding Capstone (Agents for Business track).

## Problem

Sales and account teams lose deals not because pipeline data is wrong,
but because the signal that a deal is slipping gets buried in a static
CRM export. Reviews are still largely manual — someone scans a
spreadsheet and flags deals from memory, which is slow and
inconsistent, and gets worse as pipeline size grows. PipelineWatch
replaces that manual scan with a repeatable, explainable agent pipeline
that turns raw CRM data into a prioritized, plain-English risk report.

## Architecture

```
 pipeline_deals.csv
        |
        v
 +------------------+      loads & validates raw deal records
 |   Data Agent      |      (rejects malformed rows)
 +------------------+
        |  state: data_agent_output
        v
 +------------------+      loads risk rules from SKILL.md (Agent Skill)
 | Risk-Scoring Agent|      calls score_all_deals tool (deterministic)
 +------------------+      excludes notes field from scoring (security)
        |  state: risk_scoring_output
        v
 +------------------+      drafts plain-English exec summary,
 |  Insights Agent    |      ranked by dollars at risk
 +------------------+
        |
        v
 Executive summary (Medium/High risk deals, ranked by $)
```

The three agents are chained with ADK's `SequentialAgent`, each with a
single responsibility and its own tool(s), rather than one large prompt
doing everything. See `agents.py` and `tools.py` for the implementation,
and `SKILL.md` for the swappable risk-scoring rules.



## Setup

```bash
git clone <this-repo-url>
cd pipelinewatch
pip install -r requirements.txt
```

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
using a personal Google account, then:

```bash
export GOOGLE_API_KEY="your-key-here"
```

## Run

**Run the eval (no API key needed):**

```bash
python eval.py
```

Checks the deterministic risk-scoring logic against 13 hand-labeled
sample deals and prints accuracy.

**Run the full agent pipeline:**

```bash
python main.py
```

Runs all three agents end-to-end and prints the final executive summary.

## Files

| File | Purpose |
|---|---|
| `agents.py` | ADK agent definitions and the SequentialAgent pipeline |
| `tools.py` | Deterministic data validation and risk-scoring functions used as agent tools |
| `SKILL.md` | The Agent Skill: risk-scoring rules and eval labels, swappable without touching code |
| `pipeline_deals.csv` | Sample synthetic CRM data (15 deals, 4 accounts) |
| `main.py` | Entry point to run the full agent pipeline |
| `eval.py` | Standalone accuracy check against labeled expected results |

## Security notes

- Free-text `notes` fields are never passed into risk-scoring logic —
  display-only, to avoid prompt injection via CRM free text.
- Malformed rows (non-numeric amounts, negative day counts) are rejected
  during data loading rather than silently passed through.
- Customer contact names/emails are never included in generated
  summaries (the sample data intentionally omits them).

## Notes on model/version

Built and tested against `google-adk` 2.3.0 and the `gemini-2.5-flash`
model. If you're running this after an ADK update, check
`agents.py`'s `MODEL` constant against the model names currently
available in Google AI Studio.
