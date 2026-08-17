import json
import requests

with open("data/processed/huang_cannot_self_correct.json") as f:
    data = json.load(f)

    chunk = data["chunks"][5]

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
}

response = requests.post(url, json=payload)
result = response.json()

content = result["message"]["content"]
claims = json.loads(content)

print(json.dumps(claims, indent=2))
