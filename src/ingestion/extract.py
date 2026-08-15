from pypdf import PdfReader
from clean_text import clean_text

def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() for page in reader.pages]
    return "\n\n".join(pages)
reader = PdfReader("data/papers/huang_2310.01798.pdf")


if __name__ == "__main__":
    print(len(reader.pages))


    text = extract_text("data/papers/huang_2310.01798.pdf")
    cleaned = clean_text(text)
    paragraphs = cleaned.split("\n\n")
    print(len(paragraphs))
    print(cleaned[:1000])