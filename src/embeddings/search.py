import json
import requests
from src.ingestion.papers import papers

url = "http://localhost:11434/api/embed"

def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x ** 2 for x in a) ** 0.5
    magnitude_b = sum(y ** 2 for y in b) ** 0.5
    return dot_product / (magnitude_a * magnitude_b)

def embed_query(text):
    data = {"model": "mxbai-embed-large", "input": text}
    response = requests.post(url, json=data)
    result = response.json()
    return result["embeddings"][0]


def search(query, top_k=5):
    query_vector = embed_query(query)
    results = []

    for paper in papers:
        path = f"data/embedded/{paper['name']}.json"
        with open(path) as f:
            data = json.load(f)

        for chunk, embedding in zip(data["chunks"], data["embeddings"]):
            similarity = cosine_similarity(query_vector, embedding)
            results.append({
                "paper_name": paper["name"],
                "chunk": chunk,
                "similarity": similarity,
            })

    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    top_results = search("does self-correction work without external feedback?")
    for r in top_results:
        print(f"{r['paper_name']} ({r['similarity']:.3f}): {r['chunk'][:150]}")