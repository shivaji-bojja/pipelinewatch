"""
tools.py

Deterministic, testable functions used as ADK tools by the PipelineWatch
agents. Keeping the actual scoring math here (not left to the LLM alone)
means the risk labels are reproducible and match the eval table in
SKILL.md exactly -- the LLM's job is to orchestrate and narrate, not to
do arithmetic on days-since-activity.
"""

import csv
import os
from typing import Any


OPEN_STAGES = {"Discovery", "Proposal", "Negotiation"}


def load_and_validate_deals(csv_path: str) -> dict[str, Any]:
    """Load deal records from a CSV file and validate them.

    Rejects rows with non-numeric/negative amounts or negative/missing
    days_since_last_activity, per the security notes in SKILL.md. This
    is the Data Agent's tool.

    Args:
        csv_path: path to the pipeline deals CSV file.

    Returns:
        A dict with 'valid_deals' (list of dicts) and 'rejected' (list of
        dicts describing any rows that failed validation).
    """
    valid_deals = []
    rejected = []

    if not os.path.exists(csv_path):
        return {"valid_deals": [], "rejected": [], "error": f"File not found: {csv_path}"}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reason = _validate_row(row)
            if reason:
                rejected.append({"deal_id": row.get("deal_id", "unknown"), "reason": reason})
                continue
            row["amount_usd"] = float(row["amount_usd"])
            row["days_since_last_activity"] = int(row["days_since_last_activity"])
            row["stage_regressed"] = row["stage_regressed"].strip().lower() == "yes"
            valid_deals.append(row)

    return {"valid_deals": valid_deals, "rejected": rejected}


def _validate_row(row: dict[str, str]) -> str | None:
    try:
        amount = float(row.get("amount_usd", ""))
        if amount < 0:
            return "negative amount_usd"
    except (ValueError, TypeError):
        return "non-numeric amount_usd"

    try:
        days = int(row.get("days_since_last_activity", ""))
        if days < 0:
            return "negative days_since_last_activity"
    except (ValueError, TypeError):
        return "missing or non-numeric days_since_last_activity"

    return None


def load_skill(skill_path: str) -> str:
    """Load the risk-scoring skill definition as plain text.

    This is the Agent Skill referenced by the Risk-Scoring Agent -- the
    rules live in this file, not in agent code or the prompt, so they can
    be swapped without redeploying the agent.

    Args:
        skill_path: path to SKILL.md.

    Returns:
        The raw skill file contents.
    """
    with open(skill_path, encoding="utf-8") as f:
        return f.read()


def score_deal(
    stage: str,
    days_since_last_activity: int,
    stage_regressed: bool,
) -> dict[str, Any]:
    """Apply the SKILL.md risk rules to a single deal.

    Only Discovery, Proposal, and Negotiation stages are scored -- Closed
    Won / Closed Lost deals are out of scope per SKILL.md and should be
    filtered out by the caller before or after calling this tool.

    Boundary rule: days_since_last_activity == 10 counts as Medium (the
    Medium tier is defined as 10-20 days inclusive).

    Args:
        stage: the deal's current pipeline stage.
        days_since_last_activity: days since last logged activity.
        stage_regressed: whether the deal has moved backward a stage.

    Returns:
        A dict with 'risk_level' (Low/Medium/High) and 'risk_reasons'
        (list of short strings).
    """
    reasons = []

    if days_since_last_activity >= 21:
        tier = "High"
        reasons.append(f"{days_since_last_activity} days since last activity")
    elif days_since_last_activity >= 10:
        tier = "Medium"
        reasons.append(f"{days_since_last_activity} days since last activity")
    else:
        tier = "Low"

    if stage_regressed:
        reasons.append("stage regressed")
        if tier == "Low":
            tier = "Medium"
        elif tier == "Medium":
            tier = "High"
        # High stays High

    return {"risk_level": tier, "risk_reasons": reasons}


def score_all_deals(valid_deals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score every open deal and return them ranked by amount, descending.

    This is a convenience wrapper the Risk-Scoring Agent calls after
    load_and_validate_deals -- it filters to open stages, applies
    score_deal to each, and sorts by amount_usd so the biggest at-risk
    dollars surface first.
    """
    scored = []
    for deal in valid_deals:
        if deal["stage"] not in OPEN_STAGES:
            continue
        result = score_deal(
            stage=deal["stage"],
            days_since_last_activity=deal["days_since_last_activity"],
            stage_regressed=deal["stage_regressed"],
        )
        scored.append({**deal, **result})

    scored.sort(key=lambda d: d["amount_usd"], reverse=True)
    return scored


def total_at_risk(scored_deals: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the exact total dollars at risk from scored deals.

    Deliberately a plain Python sum, not left to the LLM to add up in
    free text -- LLMs are unreliable at exact arithmetic over multiple
    numbers, and a wrong total in the executive summary would undermine
    the whole point of an evaluable, trustworthy pipeline. The
    Insights Agent should call this tool and quote its result directly
    rather than computing the total itself.

    Args:
        scored_deals: the output of score_all_deals.

    Returns:
        A dict with 'total_usd' (float) and 'flagged_count' (int),
        counting only Medium/High risk deals.
    """
    at_risk = [d for d in scored_deals if d["risk_level"] in ("Medium", "High")]
    return {
        "total_usd": sum(d["amount_usd"] for d in at_risk),
        "flagged_count": len(at_risk),
    }
