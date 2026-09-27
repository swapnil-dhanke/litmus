import json
from pathlib import Path

from chunker import group_into_chunks, split_into_sentences
from clean_text import clean_text
from extract import extract_text
from papers import papers


def main():
    """Extract and chunk each paper once, writing one JSON file per paper."""
    paper_dir = Path("data/papers")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    for paper in papers:
        text = clean_text(extract_text(paper_dir / f"{paper['name']}.pdf"))
        chunks = group_into_chunks(split_into_sentences(text), separator=" ")
        result = {
            "paper_id": paper["id"],
            "paper_name": paper["name"],
            "chunks": chunks,
        }

        output_path = output_dir / f"{paper['name']}.json"
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False)

        print(f"{paper['name']}: {len(chunks)} chunks")


if __name__ == "__main__":
    main()
