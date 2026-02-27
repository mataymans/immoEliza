import re
from bs4 import BeautifulSoup

from utils import (
    clean_number_text,
    extract_first_int,
    extract_first_float,
    yesno_to_bin,
    normalize_price_from_text,
)


def parse_h4_kv(soup: BeautifulSoup) -> dict:
    """
    Robust label/value extraction:
    - Prefer next sibling
    - If missing, try parent's next sibling
    """
    data = {}
    for h4 in soup.find_all("h4"):
        label = h4.get_text(" ", strip=True)
        if not label:
            continue

        value_el = h4.find_next_sibling()
        if not value_el and h4.parent:
            value_el = h4.parent.find_next_sibling()

        value = value_el.get_text(" ", strip=True) if value_el else None
        data[label] = value
    return data


def first_present(data: dict, *keys):
    for k in keys:
        v = data.get(k)
        if v:
            return v
    return None


def parse_immovlan_id(text: str):
    m = re.search(r"\bRB[A-Z]\d+\b", text)
    return m.group(0) if m else None


def parse_locality(text: str):
    # simple: grab "#### City"
    m = re.search(r"\b(\d{4})\s+([A-Za-zÀ-ÿ' -]+)\b", text)
    return m.group(2).strip() if m else None


def parse_detail(html: str, url: str, province: str, type_seed: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    kv = parse_h4_kv(soup)

    price = normalize_price_from_text(text)

    immovlan_id = parse_immovlan_id(text)
    locality = parse_locality(text)

    bedrooms = extract_first_int(first_present(kv, "Number of bedrooms", "Bedrooms"))
    living_area = extract_first_float(
        first_present(kv, "Living area", "Livable surface", "Habitable surface")
    )

    furnished = yesno_to_bin(first_present(kv, "Furnished"))
    terrace = yesno_to_bin(first_present(kv, "Terrace"))
    garden = yesno_to_bin(first_present(kv, "Garden"))
    facades = extract_first_int(first_present(kv, "Number of facades", "Number of frontages"))
    pool = yesno_to_bin(first_present(kv, "Swimming pool"))

    land_surface = extract_first_float(first_present(kv, "Total land surface", "Land surface"))

    # kitchen equipped: very heuristic
    kitchen_equipped = None
    ktxt = first_present(kv, "Kitchen equipment", "Equipped kitchen")
    if ktxt:
        t = ktxt.lower()
        kitchen_equipped = 1 if ("equipped" in t or "installed" in t or "fitted" in t) else 0

    building_state = first_present(kv, "State of the property", "Condition")

    # Mandatory columns later; here we just output raw normalized fields
    return {
        "immovlan_id": immovlan_id,
        "url": url,
        "province": province,
        "property_type": type_seed,  # house/apartment seed from collector
        "locality": locality,
        "price_eur": price,
        "bedrooms": bedrooms,
        "living_area_m2": living_area,
        "kitchen_equipped": kitchen_equipped,
        "furnished": furnished,
        "terrace": terrace,
        "garden": garden,
        "facades": facades,
        "swimming_pool": pool,
        "land_surface_m2": land_surface,
        "building_state": building_state,
        # placeholders (filled as None if unknown)
        "subtype": None,
        "sale_type": 0,  # keep regular by default
        "open_fire": None,
        "terrace_area_m2": None,
        "garden_area_m2": None,
        "plot_surface_m2": None,
    }