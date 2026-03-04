import json
import re
import time
from urllib.parse import urljoin

THIN_SPACES = ["\u202F", "\u00A0"]  # narrow no-break space, nbsp


def read_jsonl(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
    except FileNotFoundError:
        return


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def clean_number_text(s: str) -> str:
    if s is None:
        return ""
    for sp in THIN_SPACES:
        s = s.replace(sp, "")
    return s.strip()


def extract_first_int(s: str):
    if not s:
        return None
    s = clean_number_text(s)
    m = re.search(r"\d+", s.replace(" ", "").replace(".", "").replace(",", ""))
    return int(m.group(0)) if m else None


def extract_first_float(s: str):
    if not s:
        return None
    s = clean_number_text(s)
    m = re.search(r"(\d+(?:[.,]\d+)?)", s)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def yesno_to_bin(s: str):
    if s is None:
        return None
    t = s.strip().lower()
    if t in {"yes", "oui", "ja", "true"}:
        return 1
    if t in {"no", "non", "nee", "false"}:
        return 0
    return None


def normalize_price_from_text(text: str):
    """
    Captures prices with € AFTER or BEFORE the number.
    Handles spaces / dots / commas / thin spaces.
    """
    if not text:
        return None
    # 1) "250 000 €"  2) "€ 250 000"
    m = re.search(r"(\d[\d\s.,\u202F\u00A0]*)\s*€", text)
    if not m:
        m = re.search(r"€\s*(\d[\d\s.,\u202F\u00A0]*)", text)
    if not m:
        return None
    raw = clean_number_text(m.group(1))
    raw = raw.replace(" ", "").replace(".", "").replace(",", "")
    return int(raw) if raw.isdigit() else None


def safe_urljoin(base: str, href: str):
    return urljoin(base, href)


def sleep_jitter(base=0.4):
    time.sleep(base)