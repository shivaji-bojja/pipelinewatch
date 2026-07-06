"""
main.py

Run the full PipelineWatch pipeline end-to-end using an in-memory ADK
runner -- suitable for a Kaggle notebook cell or local run.

Setup:
    pip install google-adk
    export GOOGLE_API_KEY="your-gemini-api-key"   # from Google AI Studio
    python main.py
"""

import asyncio
import os

import httpx
from google.adk.runners import InMemoryRunner
from google.genai.errors import ServerError

from agents import pipeline_watch

MAX_RETRIES = 4


async def main() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit(
            "GOOGLE_API_KEY is not set. Get a key from Google AI Studio "
            "and run: export GOOGLE_API_KEY='your-key-here'"
        )

    runner = InMemoryRunner(agent=pipeline_watch, app_name="pipeline_watch")

    prompt = (
        "Run the full pipeline analysis: load the deal data, score risk, "
        "and produce the executive summary of at-risk deals."
    )

    # run_debug is async in this ADK version -- must be awaited, not
    # called directly, or Python hands back an un-run coroutine object.
    # Wrapped in a small retry loop: transient network drops
    # (httpx.ReadError) during a long-lived LLM call are common and not
    # a code bug -- worth a couple of automatic retries before giving up.
    events = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            events = await runner.run_debug(prompt)
            break
        except (httpx.ReadError, ServerError) as e:
            print(f"Transient error on attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt == MAX_RETRIES:
                raise
            # Longer backoff for 503s -- "high demand" errors from Google's
            # side tend to need more than a couple seconds to clear.
            await asyncio.sleep(5 * attempt)

    print("\n" + "=" * 60)
    print("FINAL EVENTS")
    print("=" * 60)
    for event in events:
        author = getattr(event, "author", "unknown")
        if getattr(event, "content", None) and event.content.parts:
            printed_any = False
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(f"\n[{author}]\n{part.text}")
                    printed_any = True
            if not printed_any:
                print(f"\n[{author}] (non-text event, e.g. tool call/result)")
        else:
            print(f"\n[{author}] (empty event)")


if __name__ == "__main__":
    asyncio.run(main())
