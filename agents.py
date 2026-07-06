"""
agents.py

Defines the three PipelineWatch agents and wires them into a single
SequentialAgent, per the course's multi-agent (ADK) pattern:

    Data Agent -> Risk-Scoring Agent -> Insights Agent

Each agent has one job and its own tools. The Risk-Scoring Agent's rules
live in SKILL.md (loaded via the load_skill tool), not in this file or
in the prompt -- that's the Agent Skill piece.

Requires a Gemini API key set as the GOOGLE_API_KEY environment variable
before running (see README.md).
"""

import os

from google.adk.agents import Agent, SequentialAgent

from tools import load_and_validate_deals, load_skill, score_all_deals, total_at_risk

MODEL = "gemini-2.5-flash"

CSV_PATH = os.path.join(os.path.dirname(__file__), "pipeline_deals.csv")
SKILL_PATH = os.path.join(os.path.dirname(__file__), "SKILL.md")


data_agent = Agent(
    name="data_agent",
    model=MODEL,
    description="Loads and validates raw CRM pipeline data.",
    instruction=(
        "Call load_and_validate_deals with csv_path="
        f"'{CSV_PATH}' to load the pipeline data. "
        "Report how many deals were loaded successfully and list any "
        "rejected rows with their reasons. Then pass the valid deals "
        "along unchanged -- do not alter, summarize, or drop any fields."
    ),
    tools=[load_and_validate_deals],
    output_key="data_agent_output",
)


risk_scoring_agent = Agent(
    name="risk_scoring_agent",
    model=MODEL,
    description="Scores open deals for risk using the SKILL.md rule set.",
    instruction=(
        f"First call load_skill with skill_path='{SKILL_PATH}' to read "
        "the risk-scoring rules. Then take the valid_deals list produced "
        "by the previous agent (available in state as "
        "data_agent_output) and call score_all_deals on it to compute "
        "risk levels. Do not compute risk levels yourself -- always use "
        "the score_all_deals tool so results are consistent and "
        "reproducible. Return the full scored, ranked list, and briefly "
        "note which deals are Medium or High risk."
    ),
    tools=[load_skill, score_all_deals],
    output_key="risk_scoring_output",
)


insights_agent = Agent(
    name="insights_agent",
    model=MODEL,
    description="Writes a plain-English executive summary of at-risk deals.",
    # This agent gets exactly one tool -- total_at_risk -- and no others.
    # Everything else (risk levels, ranking) was already computed
    # deterministically upstream; the one number this agent would
    # otherwise have to compute itself in free text is the sum of
    # flagged deal amounts, and LLMs are unreliable at exact arithmetic
    # over several numbers. Giving it a tool for that one calculation
    # removes the only place a wrong number could sneak into the output.
    instruction=(
        "Using the scored deals in state as risk_scoring_output, write a "
        "short executive summary for a sales manager. Include only "
        "Medium and High risk deals, ordered by dollar amount descending. "
        "For each, state the deal name, account, amount, risk level, and "
        "the reason(s) it was flagged, in one sentence. "
        "Call the total_at_risk tool with the full list of scored deals "
        "to get the exact total -- do not add the amounts up yourself. "
        "Quote the tool's total_usd value exactly as your closing line: "
        "'Total dollars at risk: $X.' "
        "Do not include any customer contact names or emails even if "
        "present in the data -- account and deal names only. Keep the "
        "whole summary under 200 words."
    ),
    tools=[total_at_risk],
    output_key="executive_summary",
)


pipeline_watch = SequentialAgent(
    name="pipeline_watch",
    description=(
        "End-to-end pipeline risk analysis: loads deal data, scores risk "
        "against the SKILL.md rules, and produces an executive summary."
    ),
    # SequentialAgent (not a parallel/routing pattern) because each stage
    # strictly depends on the previous one's output -- there's no
    # meaningful parallelism to exploit, and a linear handoff is the
    # simplest thing that's still correct and easy to debug agent-by-agent.
    sub_agents=[data_agent, risk_scoring_agent, insights_agent],
)
