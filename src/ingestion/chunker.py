import re

from clean_text import clean_text
from extract import extract_text


# text = """hello, my name is swapnil dhanke, my age is 26 this is a test pearagraph for chunking.

#         I dont know what I am writing but I am having fun like this not sure what to write hehe
#         we are currently studying chunking feels slow but all part of the process i guess.

#         okay we have opted for self correction with LLMs, we are building litmus which is a tool that
#         finds contradictions between research papers and documents"""

# paragraphs = text.split("\n\n")

# print (len(paragraphs))
# print (paragraphs)

def group_into_chunks(paragraphs, max_words , separator = "\n\n"):
    chunks = []
    current_chunk = []
    current_word_count = 0

    for paragraph in paragraphs:
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
    text = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?]) +", text)
    return sentences

text = extract_text("data/papers/huang_2310.01798.pdf")
cleaned = clean_text(text)
sentences = split_into_sentences(cleaned)
chunks = group_into_chunks(sentences, max_words=250, separator=" ")

if __name__ == "__main__":
    print(len(chunks))
    print(chunks[0]) 

# print(len(sentences))
# print(sentences[:3])

# result = group_into_chunks(paragraphs, 100)
# print(len(result))
# print(result)