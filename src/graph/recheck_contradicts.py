from judge_claims import judge_pair
from neo4j import GraphDatabase
import csv

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


def get_contradicts_pairs():
    query = """
    MATCH (a:Claim)-[:CONTRADICTS]->(b:Claim)
    MATCH (a)-[:EXTRACTED_FROM]->(pa:Paper)
    MATCH (b)-[:EXTRACTED_FROM]->(pb:Paper)
    RETURN a.text AS text_a, pa.name AS paper_a, b.text AS text_b, pb.name AS paper_b
    """
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


pairs = get_contradicts_pairs()
print(f"Re-checking {len(pairs)} existing CONTRADICTS pairs with improved prompt\n")

counts = {"agrees": 0, "contradicts": 0, "unrelated": 0}

for pair in pairs:
    claim_a = {"text": pair["text_a"], "paper_name": pair["paper_a"]}
    claim_b = {"text": pair["text_b"], "paper_name": pair["paper_b"]}
    new_relationship = judge_pair(claim_a, claim_b)
    counts[new_relationship] += 1
    if new_relationship != "contradicts":
        print(f"RECLASSIFIED to {new_relationship}:")
        print(f"  [{pair['paper_a']}] {pair['text_a']}")
        print(f"  [{pair['paper_b']}] {pair['text_b']}\n")

print(f"\nStill contradicts: {counts['contradicts']}/{len(pairs)}")
print(f"Reclassified to agrees: {counts['agrees']}/{len(pairs)}")
print(f"Reclassified to unrelated: {counts['unrelated']}/{len(pairs)}")