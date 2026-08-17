import csv
import json
import random
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


def sample_pairs(relationship_type, limit=25):
    query = f"""
    MATCH (a:Claim)-[:{relationship_type}]-(b:Claim)
    MATCH (a)-[:EXTRACTED_FROM]->(pa:Paper)
    MATCH (b)-[:EXTRACTED_FROM]->(pb:Paper)
    RETURN elementId(a) AS id_a, a.text AS text_a, pa.name AS paper_a,
           elementId(b) AS id_b, b.text AS text_b, pb.name AS paper_b
    ORDER BY rand()
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(query, limit=limit)
        return [dict(record) for record in result]


agrees = [(p, "agrees") for p in sample_pairs("AGREES_WITH", 25)]
contradicts = [(p, "contradicts") for p in sample_pairs("CONTRADICTS", 25)]

pairs = agrees + contradicts
random.shuffle(pairs)

pipeline_lookup = {}

with open("data/eval_labeling_sheet.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["pair_id", "paper_a", "text_a", "paper_b", "text_b", "human_label"])
    for pair_id, (pair, pipeline_label) in enumerate(pairs):
        writer.writerow([pair_id, pair["paper_a"], pair["text_a"], pair["paper_b"], pair["text_b"], ""])
        pipeline_lookup[pair_id] = pipeline_label

with open("data/eval_pipeline_labels.json", "w") as f:
    json.dump(pipeline_lookup, f, indent=2)

print("Saved data/eval_labeling_sheet.csv — open it, fill in human_label with agrees/contradicts/unrelated.")
print("Do NOT open eval_pipeline_labels.json until you're done labeling.")
