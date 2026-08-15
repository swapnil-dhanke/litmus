from papers import papers
from clean_text import clean_text
from extract import extract_text
import chunker
import json

for paper in papers:

    save_path = f"data/papers/{paper['name']}.pdf"

    text = extract_text(save_path)
    text = clean_text(text)
    sentences = chunker.split_into_sentences(text)
    chunks = chunker.group_into_chunks(sentences, max_words=250, separator=" ")

    result = {
        "paper_id": paper["id"],
        "paper_name": paper["name"],
        "chunks": chunks,
    }

    output_path = f"data/processed/{paper['name']}.json"

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"{paper['name']}: {len(chunks)} chunks")
