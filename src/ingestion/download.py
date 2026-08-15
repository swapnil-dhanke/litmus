import requests

def download_pdf(url, save_path):
    response = requests.get(url)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)

if __name__ == "__main__":
    download_pdf("https://arxiv.org/pdf/2310.01798", "data/papers/huang_2310.01798.pdf")

