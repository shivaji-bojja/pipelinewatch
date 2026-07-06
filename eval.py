"""
eval.py

Checks the deterministic risk-scoring logic in tools.py against the
hand-labeled expected results in SKILL.md's eval table. This runs with
no Gemini API key required, since scoring itself is pure Python -- it
validates the rules the Risk-Scoring Agent's tool applies, independent
of any LLM output.

Run: python eval.py
"""

import os

from tools import load_and_validate_deals, score_all_deals

CSV_PATH = os.path.join(os.path.dirname(__file__), "pipeline_deals.csv")

# Expected risk levels from SKILL.md's eval table.
# D007 and D015 are Closed Won / Closed Lost and are excluded from scoring.
EXPECTED = {
    "D001": "Low",
    "D002": "High",
    "D003": "High",
    "D004": "Low",
    "D005": "High",
    "D006": "Low",
    "D008": "High",
    "D009": "Medium",
    "D010": "Medium",
    "D011": "Low",
    "D012": "High",
    "D013": "Low",
    "D014": "High",
}


def run_eval() -> None:
    result = load_and_validate_deals(CSV_PATH)
    if result.get("error"):
        raise SystemExit(result["error"])

    if result["rejected"]:
        print("Rejected rows during validation:")
        for r in result["rejected"]:
            print(f"  - {r['deal_id']}: {r['reason']}")

    scored = score_all_deals(result["valid_deals"])
    scored_by_id = {d["deal_id"]: d for d in scored}

    correct = 0
    total = len(EXPECTED)

    print(f"\n{'deal_id':<8} {'expected':<10} {'actual':<10} {'match':<6} reasons")
    print("-" * 70)

    for deal_id, expected_level in EXPECTED.items():
        deal = scored_by_id.get(deal_id)
        if deal is None:
            print(f"{deal_id:<8} {expected_level:<10} {'MISSING':<10} {'NO':<6}")
            continue
        actual_level = deal["risk_level"]
        is_match = actual_level == expected_level
        correct += int(is_match)
        print(
            f"{deal_id:<8} {expected_level:<10} {actual_level:<10} "
            f"{'YES' if is_match else 'NO':<6} {', '.join(deal['risk_reasons'])}"
        )

    print("-" * 70)
    print(f"Accuracy: {correct}/{total} ({correct / total:.0%})")


if __name__ == "__main__":
    run_eval()
