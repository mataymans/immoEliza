import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.utils import read_jsonl, append_jsonl
from src.get_with_retries import get_with_retries
from src.parse_details import parse_detail

URLS_FILE = "data/urls.jsonl"
OUT_FILE = "data/raw_rows.jsonl"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-GB,en;q=0.9",
}

BAD_KEYWORDS = ["viager", "life sale", "life annuity", "bouquet", "rente"]


def is_life_sale(html_or_text: str) -> bool:
    t = html_or_text.lower()
    return any(k in t for k in BAD_KEYWORDS)


def scrape_one(item: dict) -> dict | None:
    url = item["url"]
    province = item.get("province")
    type_seed = item.get("type_seed")

    with requests.Session() as s:
        r = get_with_retries(url, headers=HEADERS, session=s)
        if not r or getattr(r, "status_code", 0) != 200:
            return None

        html = r.text
        if is_life_sale(html):
            return None

        row = parse_detail(html, url=url, province=province, type_seed=type_seed)
        # drop rows with no ID or no price (usually broken parses)
        if not row.get("immovlan_id"):
            return None
        return row


def scrape_details(max_workers=24):
    items = list(read_jsonl(URLS_FILE) or [])

    # resume: skip already scraped IDs + URLs
    done_ids = set()
    done_urls = set()
    for r in read_jsonl(OUT_FILE) or []:
        if r.get("immovlan_id"):
            done_ids.add(r["immovlan_id"])
        if r.get("url"):
            done_urls.add(r["url"])

    # BUGFIX: previously compared against an always-empty set()
    todo = [it for it in items if it.get("url") and it["url"] not in done_urls]

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(scrape_one, it) for it in todo]
        for fut in as_completed(futures):
            row = fut.result()
            if not row:
                continue
            if row["immovlan_id"] in done_ids:
                continue
            done_ids.add(row["immovlan_id"])
            append_jsonl(OUT_FILE, row)


def main():
    scrape_details(max_workers=24)


if __name__ == "__main__":
    main()