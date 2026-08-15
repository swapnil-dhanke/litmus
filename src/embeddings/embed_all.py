import json
import requests
from src.ingestion.papers import papers

url = "http://localhost:11434/api/embed"

for paper in papers:
    input_path = f"data/processed/{paper['name']}.json"

    with open(input_path) as f:
        data = json.load(f)

    request_data = {
        "model": "mxbai-embed-large",
        "input": data["chunks"],
    }
    response = requests.post(url, json=request_data)
    result = response.json()

    data["embeddings"] = result["embeddings"]

    output_path = f"data/embedded/{paper['name']}.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"{paper['name']}: {len(data['embeddings'])} embeddings")