from pypdf import PdfReader


def extract_text(pdf_path):
    """Extract a PDF's text without doing any work when this module is imported."""
    reader = PdfReader(pdf_path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


if __name__ == "__main__":
    from clean_text import clean_text

    reader = PdfReader("data/papers/huang_2310.01798.pdf")
    print(len(reader.pages))
    text = extract_text("data/papers/huang_2310.01798.pdf")
    cleaned = clean_text(text)
    print(len(cleaned.split("\n\n")))
    print(cleaned[:1000])
