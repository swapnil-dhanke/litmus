import requests
import numpy as np
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


def embed_text(text):
    url = "http://localhost:11434/api/embed"
    payload = {"model": "mxbai-embed-large", "input": text}
    response = requests.post(url, json=payload)
    return response.json()["embeddings"][0]


def search_claims(query, top_k=5):
    """Search for claims relevant to a topic. Returns a list of (similarity, claim text, paper name, verified, match_score)."""
    query_vector = np.array(embed_text(query))

    with driver.session() as session:
        result = session.run("""
            MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
            RETURN c.text AS text, c.embedding AS embedding, p.name AS paper_name,
                   c.verified AS verified, c.match_score AS match_score
        """)
        claims = [dict(record) for record in result]

    scored = []
    for claim in claims:
        similarity = np.dot(query_vector, np.array(claim["embedding"]))
        scored.append((similarity, claim["text"], claim["paper_name"], claim["verified"], claim["match_score"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def find_relationships(claim_text, top_k=5):
    """Given a description of a claim, find what other claims agree with or contradict it."""
    query_vector = np.array(embed_text(claim_text))

    with driver.session() as session:
        result = session.run(
            """
            MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
            RETURN elementId(c) AS id, c.text AS text, c.embedding AS embedding, p.name AS paper_name,
                   c.verified AS verified, c.match_score AS match_score
            """)
        claims = [dict(record) for record in result]

    best_match = max(claims, key=lambda c: np.dot(query_vector, np.array(c["embedding"])))

    with driver.session() as session:
        agrees = session.run("""
            MATCH (c:Claim)-[:AGREES_WITH]-(other:Claim)-[:EXTRACTED_FROM]->(p:Paper)
            WHERE elementId(c) = $claim_id
            RETURN other.text AS text, p.name AS paper_name, other.verified AS verified, other.match_score AS match_score
        """, claim_id=best_match["id"])
        agreements = [dict(r) for r in agrees][:top_k]

        contradicts = session.run("""
            MATCH (c:Claim)-[:CONTRADICTS]-(other:Claim)-[:EXTRACTED_FROM]->(p:Paper)
            WHERE elementId(c) = $claim_id
            RETURN other.text AS text, p.name AS paper_name, other.verified AS verified, other.match_score AS match_score
        """, claim_id=best_match["id"])
        contradictions = [dict(r) for r in contradicts][:top_k]

    return {
        "matched_claim": best_match["text"],
        "matched_paper": best_match["paper_name"],
        "matched_verified": best_match["verified"],
        "agreements": agreements,
        "contradictions": contradictions,
    }


if __name__ == "__main__":
    result = find_relationships("self-correction improves performance")
    print(result["matched_claim"], "—", result["matched_paper"])
    print("AGREES:", result["agreements"])
    print("CONTRADICTS:", result["contradictions"])