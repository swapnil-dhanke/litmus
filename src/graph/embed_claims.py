import requests
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))


def get_all_claims():
    query = "MATCH (c:Claim) RETURN elementId(c) AS id, c.text AS text"
    with driver.session() as session:
        result = session.run(query)
        return [{"id": record["id"], "text": record["text"]} for record in result]


def save_embedding(claim_id, embedding):
    query = "MATCH (c:Claim) WHERE elementId(c) = $id SET c.embedding = $embedding"
    with driver.session() as session:
        session.run(query, id=claim_id, embedding=embedding)


claims = get_all_claims()
print(f"found {len(claims)} claims")

url = "http://localhost:11434/api/embed"
batch_size = 50

for start in range(0, len(claims), batch_size):
    batch = claims[start:start + batch_size]
    texts = [c["text"] for c in batch]

    payload = {"model": "mxbai-embed-large", "input": texts}
    response = requests.post(url, json=payload)
    result = response.json()
    embeddings = result["embeddings"]

    for claim, embedding in zip(batch, embeddings):
        save_embedding(claim["id"], embedding)

    print(f"embedded {start + len(batch)} / {len(claims)}")