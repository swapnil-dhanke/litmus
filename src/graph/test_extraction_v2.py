"""
Read-only comparison of the OLD (Phase 2 original) vs NEW (refined) claim-extraction prompt +
heuristic filter, run against real chunks known to have triggered each of the four documented
extraction failure modes (see ENGINEERING_LOG.md). Writes nothing to Neo4j — this is purely for
validating the fix before deciding whether to re-run extraction on the full corpus.

Run locally (requires Ollama running on localhost:11434):
    python3 -m src.graph.test_extraction_v2
"""
import json
import requests
from src.graph.process_each_claim import extract_claims as extract_claims_new
from src.graph.process_each_claim import passes_heuristic_filter

# The exact original Phase 2 prompt, preserved here only for this before/after comparison.
OLD_PROMPT_TEMPLATE = """Extract factual claims about LLM self-correction from this text.
Do not include section headings, titles, author names, or citation markers as claims — only include substantive factual assertions.
For each claim, include the exact sentence from the text it's based on.

Respond with JSON in this exact shape:
{{"claims": [{{"claim": "...", "source_sentence": "..."}}]}}

Text:
{chunk}"""


def extract_claims_old(chunk):
    prompt = OLD_PROMPT_TEMPLATE.format(chunk=chunk)
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"num_predict": 500},
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        content = response.json()["message"]["content"]
        claims = json.loads(content)["claims"]
        return claims if isinstance(claims, list) else []
    except (json.JSONDecodeError, KeyError, requests.exceptions.RequestException):
        return []


# Real chunks, from real processed papers, each one confirmed (via ENGINEERING_LOG.md spot-checks)
# to have actually caused one of the four documented Phase 2 failure modes.
TEST_CASES = [
    {
        "label": "Title/heading + author list (huang_cannot_self_correct, chunk 0)",
        "file": "data/processed/huang_cannot_self_correct.json",
        "chunk_index": 0,
    },
    {
        "label": "Benchmark/worked trivia example (confidence_matters, chunk 49)",
        "file": "data/processed/confidence_matters.json",
        "chunk_index": 49,
    },
]


def run_case(case):
    with open(case["file"]) as f:
        data = json.load(f)
    chunk = data["chunks"][case["chunk_index"]]

    print("=" * 100)
    print(case["label"])
    print("-" * 100)
    print("Chunk preview:", chunk[:200].replace("\n", " "), "...")
    print()

    old_claims = extract_claims_old(chunk)
    print(f"OLD prompt extracted {len(old_claims)} claim(s):")
    for c in old_claims:
        if not isinstance(c, dict):
            # The old prompt has no format guardrail against this — the model can return a
            # flat list of strings instead of {"claim": ..., "source_sentence": ...} objects.
            # Worth surfacing as its own finding, not just skipping silently.
            print(f"  - MALFORMED (not a claim object, got {type(c).__name__}): {c!r}")
            continue
        print(f"  - claim: {c.get('claim', '')!r}")
        print(f"    source: {c.get('source_sentence', '')!r}")

    print()
    new_claims = extract_claims_new(chunk)
    kept, dropped = [], []
    for c in new_claims:
        if not isinstance(c, dict) or "claim" not in c or "source_sentence" not in c:
            dropped.append((c, "missing claim/source_sentence key or malformed shape"))
            continue
        passes, reason = passes_heuristic_filter(c["claim"], c["source_sentence"])
        (kept if passes else dropped).append((c, reason))

    print(f"NEW prompt extracted {len(new_claims)} claim(s) — {len(kept)} kept, {len(dropped)} dropped by filter:")
    for c, _ in kept:
        print(f"  KEPT   - claim: {c.get('claim', '')!r}")
        print(f"           source: {c.get('source_sentence', '')!r}")
    for c, reason in dropped:
        claim_text = c.get("claim", repr(c)) if isinstance(c, dict) else repr(c)
        print(f"  DROPPED ({reason}) - claim: {claim_text!r}")
    print()


if __name__ == "__main__":
    for case in TEST_CASES:
        run_case(case)
