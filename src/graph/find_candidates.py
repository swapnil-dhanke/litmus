import numpy as np
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


def get_all_claims():
    query = """
    MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
    RETURN elementId(c) AS id, c.text AS text, c.embedding AS embedding, p.name AS paper_name
    """
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


claims = get_all_claims()
print(f"loaded {len(claims)} claims")

embeddings = np.array([c["embedding"] for c in claims])
similarity_matrix = embeddings @ embeddings.T # @ is multiply and .T is transpose

print(similarity_matrix.shape)

# threshold = 0.75 #similarity test 1 -> found 9000+ pairs no use
threshold = 0.85 

candidates = []

for i in range(len(claims)):
    for j in range(i + 1, len(claims)):
        if claims[i]["paper_name"] == claims[j]["paper_name"]:
            continue
        similarity = similarity_matrix[i][j]
        if similarity > threshold:
            candidates.append((claims[i], claims[j], similarity))

print(f"found {len(candidates)} candidate pairs")