import re


_WHITESPACE = re.compile(r"\s+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?]) +")


def group_into_chunks(paragraphs, max_words=250, separator="\n\n"):
    """Combine consecutive text units without exceeding ``max_words`` when possible."""
    if max_words <= 0:
        raise ValueError("max_words must be positive")

    chunks = []
    current_chunk = []
    current_word_count = 0

    for paragraph in paragraphs:
        if not paragraph or not paragraph.strip():
            continue

        word_count = len(paragraph.split())
        if current_word_count + word_count > max_words and current_chunk:
            chunks.append(separator.join(current_chunk))
            current_chunk = []
            current_word_count = 0

        current_chunk.append(paragraph)
        current_word_count += word_count

    if current_chunk:
        chunks.append(separator.join(current_chunk))

    return chunks


def split_into_sentences(text):
    """Normalize whitespace and split at basic sentence-ending punctuation."""
    normalized_text = _WHITESPACE.sub(" ", text).strip()
    return _SENTENCE_BOUNDARY.split(normalized_text) if normalized_text else []


def main():
    """Run the one-paper chunking example without affecting library imports."""
    from clean_text import clean_text
    from extract import extract_text

    text = extract_text("data/papers/huang_2310.01798.pdf")
    chunks = group_into_chunks(split_into_sentences(clean_text(text)), separator=" ")
    print(len(chunks))
    if chunks:
        print(chunks[0])


if __name__ == "__main__":
    main()
