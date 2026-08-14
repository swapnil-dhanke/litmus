import re

# A real messy snippet from the Huang et al. paper's fetched HTML text.
sample = (
    "have showcased promising results across a multitude of applications "
    "(Chowdhery et al., [2023](https://arxiv.org/html/2310.01798v2#bib.bib8 \"\"); "
    "Anil et al., [2023](https://arxiv.org/html/2310.01798v2#bib.bib2 \"\"); "
    "OpenAI, [2023](https://arxiv.org/html/2310.01798v2#bib.bib23 \"\"), inter alia). "
    "However, concerns about their accuracy, reasoning capabilities<!-- MathML: <math>garbage</math> -->, "
    "and the safety of their generated content have drawn significant attention."
)


def clean_text(text: str) -> str:
    # 1. Remove HTML comments, e.g. <!-- MathML: ... -->
    #    re.sub(pattern, replacement, text) finds every match of `pattern`
    #    in `text` and swaps it for `replacement` (here, nothing).
    #    ".*?" means "any characters, as few as possible" so it stops at
    #    the *first* "-->" instead of gobbling up the rest of the document.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # 2. Turn markdown links [label](url "title") into just `label`.
    #    \[([^\]]+)\]  captures the label inside [ ]  -> group 1
    #    \([^)]+\)     matches the (url "title") part and throws it away
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    return text


if __name__ == "__main__":
    print("--- BEFORE ---")
    print(sample)
    print("\n--- AFTER ---")
    print(clean_text(sample))
