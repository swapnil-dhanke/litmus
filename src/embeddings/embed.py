import requests

url = "http://localhost:11434/api/embed"
data = {
    "model": "mxbai-embed-large",
    "input": "Large language models cannot self-correct their reasoning without external feedback.",
}
response = requests.post(url, json=data)
result = response.json()

print(len(result["embeddings"][0]))
print(result["embeddings"][0][:5])