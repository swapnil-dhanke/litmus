from papers import papers
from download import download_pdf

for paper in papers:

    url = f"https://arxiv.org/pdf/{paper['id']}"
    save_path = f"data/papers/{paper['name']}.pdf"

    download_pdf(url, save_path)
    print(paper["name"])