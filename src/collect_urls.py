import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.utils import append_jsonl, read_jsonl, sleep_jitter

BASE_URL = "https://immovlan.be"
OUTPUT_FILE = "data/urls.jsonl"

HEADERS = {"User-Agent": "Mozilla/5.0"}

PROPERTY_TYPES = {"house": "house", "apartment": "apartment"}

PROVINCES = [
    "antwerp",
    "brussels",
    "east-flanders",
    "west-flanders",
    "flemish-brabant",
    "walloon-brabant",
    "hainaut",
    "liege",
    "luxembourg",
    "namur",
    "limburg",
]


def extract_detail_links(html: str):
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/en/detail/" in href:
            links.add(urljoin(BASE_URL, href))
    return links


def collect_urls(max_pages=50):
    # persistent dedupe (so reruns don’t duplicate)
    seen = set()
    for row in read_jsonl(OUTPUT_FILE) or []:
        seen.add(row["url"])

    for province in PROVINCES:
        for label, ptype in PROPERTY_TYPES.items():
            for page in range(1, max_pages + 1):
                url = (
                    f"{BASE_URL}/en/real-estate/{ptype}/for-sale"
                    f"?provinces={province}&page={page}"
                )
                print(f"[urls] {province} | {label} | page {page}")

                r = requests.get(url, headers=HEADERS, timeout=30)
                if r.status_code != 200:
                    break

                links = extract_detail_links(r.text)
                if not links:
                    break

                new = 0
                for link in links:
                    if link in seen:
                        continue
                    seen.add(link)
                    append_jsonl(
                        OUTPUT_FILE,
                        {"province": province, "type_seed": label, "url": link},
                    )
                    new += 1

                if new == 0:
                    # likely already scraped this segment
                    pass

                sleep_jitter(0.5)


def main():
    collect_urls(max_pages=50)


if __name__ == "__main__":
    main()