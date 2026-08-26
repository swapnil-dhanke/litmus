import re
import json
import requests
from neo4j import GraphDatabase
from src.ingestion.papers import papers

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))

# Fragments of our own extraction instructions — used to catch "instruction leakage"
# (the model echoing a line from its own prompt back as if it were extracted content).
# See ENGINEERING_LOG.md #incident on garbled/formula-heavy chunks.
INSTRUCTION_FRAGMENTS = [
    "extract factual claims",
    "do not include section headings",
    "only include substantive factual assertions",
    "respond with json in this exact shape",
]


def get_processed_papers():
    query = "MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper) RETURN DISTINCT p.name AS name"
    with driver.session() as session:
        result = session.run(query)
        return {record["name"] for record in result}


def save_claim(paper_id, paper_name, claim_text, source_sentence):
    query = """
    MERGE (p:Paper {id: $paper_id, name: $paper_name})
    CREATE (c:Claim {text: $claim_text, source_sentence: $source_sentence})
    CREATE (c)-[:EXTRACTED_FROM]->(p)
    """
    with driver.session() as session:
        session.run(query, paper_id=paper_id, paper_name=paper_name,
                     claim_text=claim_text, source_sentence=source_sentence)


def passes_heuristic_filter(claim_text, source_sentence):
    """Mechanical, non-LLM checks that catch the extraction failure modes documented in
    ENGINEERING_LOG.md, independent of whatever the prompt itself does or doesn't catch.
    Returns (passes: bool, reason: str) so callers can log why something was dropped."""
    if not claim_text or not source_sentence:
        return False, "missing claim or source_sentence"

    stripped_source = source_sentence.strip()

    # Headings/titles (both ALL-CAPS and normal title-case citation references) reliably lack
    # sentence-ending punctuation — a real prose sentence almost always ends in . ! or ?
    if not re.search(r"[.!?]\s*$", stripped_source):
        return False, "source_sentence has no sentence-ending punctuation (likely a heading/title)"

    # All-caps headings/titles — pulled forward from the judge-time filter (Phase 3) to
    # extraction time, so these never enter the graph in the first place.
    if stripped_source.isupper():
        return False, "source_sentence is all uppercase (likely a heading/title)"

    # Headings and short citation fragments tend to be very short; real claims/evidence
    # sentences in this corpus are consistently longer than this in practice.
    if len(stripped_source.split()) < 6:
        return False, "source_sentence too short to be a real evidence sentence"

    # Instruction leakage — the model echoing a fragment of its own extraction prompt back
    # as if it were content from the paper (observed on garbled/formula-heavy chunks).
    lowered_claim = claim_text.lower()
    lowered_source = stripped_source.lower()
    for fragment in INSTRUCTION_FRAGMENTS:
        if fragment in lowered_claim or fragment in lowered_source:
            return False, "matches our own extraction instructions (instruction leakage)"

    return True, ""


def extract_claims(chunk):
    prompt = f"""Extract factual claims about LLM self-correction from this text.

    Do not include section headings, titles, author names, or citation markers as claims —
    only include substantive factual assertions.

    Do not extract a paper's own title or a citation reference to another paper's title as a
    claim, even if it appears in normal title-case running text. For example, in the sentence
    "As CRITIC showed, tool-interactive critiquing improves accuracy," the claim is about
    tool-interactive critiquing improving accuracy — "CRITIC" is a citation reference, not a
    claim by itself, and should never be extracted as its own claim.

    Do not extract a worked example, case study, or benchmark question that the paper uses to
    illustrate its method as if it were a real factual claim the paper is making. For example, a
    paper demonstrating its method with a sample trivia question like "Which restaurant chain's
    headquarters is further north, X or Y?" is illustrating a technique, not asserting a real
    claim about self-correction — do not extract sentences from inside such an example.

    Only extract a claim if you can quote an exact, complete sentence from the text below that
    directly and specifically supports that exact claim — never a nearby or loosely related
    sentence about a different topic.

    Never repeat any part of these instructions themselves as if they were a claim or a quoted
    sentence from the text.

    For each claim, include the exact sentence from the text it's based on.

    Respond with JSON in this exact shape:
    {{"claims": [{{"claim": "...", "source_sentence": "..."}}]}}

    Text:
    {chunk}"""

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
        result = response.json()
        content = result["message"]["content"]
        claims = json.loads(content)["claims"]
        if not isinstance(claims, list):
            return []
        # The model occasionally returns a flat list of strings instead of the requested
        # {"claim": ..., "source_sentence": ...} objects (e.g. {"claims": ["some text"]}).
        # Drop anything that isn't the expected shape rather than crashing downstream.
        return [c for c in claims if isinstance(c, dict)]
    except (json.JSONDecodeError, KeyError, requests.exceptions.RequestException):
        return []


processed = get_processed_papers()

for paper in papers:
    if paper["name"] in processed:
        print(f"skipping {paper['name']} (already processed)")
        continue

    with open(f"data/processed/{paper['name']}.json") as f:
        data = json.load(f)

    total_claims = 0
    total_dropped = 0
    for i, chunk in enumerate(data["chunks"]):
        claims = extract_claims(chunk)
        kept = 0
        for claim in claims:
            if not isinstance(claim, dict) or "claim" not in claim or "source_sentence" not in claim:
                continue
            passes, reason = passes_heuristic_filter(claim["claim"], claim["source_sentence"])
            if not passes:
                total_dropped += 1
                print(f"    dropped ({reason}): {claim['claim'][:80]!r}")
                continue
            save_claim(data["paper_id"], data["paper_name"], claim["claim"], claim["source_sentence"])
            total_claims += 1
            kept += 1
        print(f"  chunk {i}: {kept} claims kept, {len(claims) - kept} dropped")

    print(f"{paper['name']}: {total_claims} claims saved, {total_dropped} dropped by heuristic filter")