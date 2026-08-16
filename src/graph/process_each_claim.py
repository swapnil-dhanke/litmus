import json
import requests
from neo4j import GraphDatabase
from src.ingestion.papers import papers

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


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


def extract_claims(chunk):
    prompt = f"""Extract factual claims about LLM self-correction from this text.
    Do not include section headings, titles, author names, or citation markers as claims — only include substantive factual assertions.
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
        # return json.loads(content)["claims"]
        claims = json.loads(content)["claims"]
        if not isinstance(claims, list):
            return []
        return claims
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
    for i, chunk in enumerate(data["chunks"]):
        claims = extract_claims(chunk)
        for claim in claims:
            if "claim" not in claim or "source_sentence" not in claim:
                continue
            save_claim(data["paper_id"], data["paper_name"], claim["claim"], claim["source_sentence"])
            total_claims += 1
        print(f"  chunk {i}: {len(claims)} claims")

    print(f"{paper['name']}: {total_claims} claims saved")