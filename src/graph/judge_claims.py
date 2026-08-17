import json
import requests
import numpy as np
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


def judge_pair(claim_a, claim_b):

    # prompt = f"""Compare these two claims about LLM self-correction and decide their relationship.

    # Claim A (from paper "{claim_a['paper_name']}"): "{claim_a['text']}"
    # Claim B (from paper "{claim_b['paper_name']}"): "{claim_b['text']}"

    # Example 1: "LLMs struggle to self-correct without feedback" and "LLMs fail to identify their own
    # reasoning errors" both conclude that self-correction doesn't work well — even though worded
    # differently, this is "agrees", NOT "contradicts".

    # Example 2: "LLMs have intrinsic self-correction ability" and "LLMs can self-correct with
    # tool-interactive critiquing" both conclude that self-correction is achievable — one emphasizes
    # it happening without external help, the other describes a specific technique that uses external
    # tools. Different mechanism or emphasis is NOT the same as opposition. Unless one claim explicitly
    # asserts that the other's mechanism does NOT work or is unnecessary, this is "agrees", NOT
    # "contradicts".

    # Only choose "contradicts" if one claim asserts something works/helps/improves and the other
    # claim asserts that same specific thing does NOT work/hurts/degrades — a genuine, direct
    # opposition, not just a different angle on a compatible idea.

    # Definitions:
    # - "agrees": both claims reach the same conclusion about the same specific question, even using
    # different words, examples, or mechanisms to reach that same conclusion.
    # - "contradicts": the claims reach OPPOSITE conclusions about the same specific question.
    # - "unrelated": the claims aren't really addressing the same specific question.

    # First, briefly state the conclusion each claim reaches. Then decide the relationship.

    # Respond with JSON in this exact shape:
    # {{"claim_a_conclusion": "...", "claim_b_conclusion": "...", "relationship": "agrees"}}"""

    prompt = f"""Compare these two claims about LLM self-correction and decide their relationship.

    Claim A (from paper "{claim_a['paper_name']}"): "{claim_a['text']}"
    Claim B (from paper "{claim_b['paper_name']}"): "{claim_b['text']}"

    Example: "LLMs struggle to self-correct without feedback" and "LLMs fail to identify their own
    reasoning errors" both conclude that self-correction doesn't work well — even though worded
    differently, this is "agrees", NOT "contradicts".

    Only choose "contradicts" if one claim asserts something works/helps/improves and the other
    claim asserts that same specific thing does NOT work/hurts/degrades — a genuine, direct
    opposition, not just a different angle on a compatible idea.

    Definitions:
    - "agrees": both claims reach the same conclusion about the same specific question, even using
    different words, examples, or mechanisms to reach that same conclusion.
    - "contradicts": the claims reach OPPOSITE conclusions about the same specific question.
    - "unrelated": the claims aren't really addressing the same specific question.

    First, briefly state the conclusion each claim reaches. Then decide the relationship.

    Respond with JSON in this exact shape:
    {{"claim_a_conclusion": "...", "claim_b_conclusion": "...", "relationship": "agrees"}}"""

    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"num_predict": 50},
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        result = response.json()
        content = result["message"]["content"]
        relationship = json.loads(content)["relationship"]
        if relationship not in ("agrees", "contradicts", "unrelated"):
            return "unrelated"
        return relationship
    except (json.JSONDecodeError, KeyError, requests.exceptions.RequestException):
        return "unrelated"


def save_relationship(id_a, id_b, relationship):
    rel_type = "AGREES_WITH" if relationship == "agrees" else "CONTRADICTS"
    query = f"""
    MATCH (a:Claim), (b:Claim)
    WHERE elementId(a) = $id_a AND elementId(b) = $id_b
    MERGE (a)-[:{rel_type}]->(b)
    """
    with driver.session() as session:
        session.run(query, id_a=id_a, id_b=id_b)


def get_all_claims():
    query = """
    MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
    RETURN elementId(c) AS id, c.text AS text, c.embedding AS embedding, p.name AS paper_name
    """
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


def run_judgment():
    claims = get_all_claims()
    print(f"loaded {len(claims)} claims")
    claims = [c for c in claims if not c["text"].isupper()]
    print(f"{len(claims)} claims after filtering headings")

    embeddings = np.array([c["embedding"] for c in claims])
    similarity_matrix = embeddings @ embeddings.T

    threshold = 0.85
    agrees_count = 0
    contradicts_count = 0

    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            if claims[i]["paper_name"] == claims[j]["paper_name"]:
                continue
            if similarity_matrix[i][j] <= threshold:
                continue

            relationship = judge_pair(claims[i], claims[j])
            if relationship == "agrees":
                save_relationship(claims[i]["id"], claims[j]["id"], "agrees")
                agrees_count += 1
            elif relationship == "contradicts":
                save_relationship(claims[i]["id"], claims[j]["id"], "contradicts")
                contradicts_count += 1

            if (agrees_count + contradicts_count) % 10 == 0:
                print(f"pair {i},{j} — agrees: {agrees_count}, contradicts: {contradicts_count}")


if __name__ == "__main__":
    run_judgment()