import json
import re
from bs4 import BeautifulSoup

from src.utils import (
    extract_first_int,
    extract_first_float,
    yesno_to_bin,
    normalize_price_from_text,
)


def parse_h4_kv(soup: BeautifulSoup) -> dict:
    """Extract label/value pairs from the visible detail blocks.

    Immovlan often uses: <h4>Label</h4> then a sibling container holding the value.
    We try (in order): next sibling, parent's next sibling, and next element that
    contains text.
    """

    data: dict[str, str] = {}
    for h4 in soup.find_all("h4"):
        label = h4.get_text(" ", strip=True)
        if not label:
            continue

        value_el = h4.find_next_sibling()
        if not value_el and h4.parent:
            value_el = h4.parent.find_next_sibling()
        if not value_el:
            # last resort: the next tag with some text
            value_el = h4.find_next(lambda tag: getattr(tag, "get_text", None) and tag.get_text(strip=True))

        value = value_el.get_text(" ", strip=True) if value_el else None
        if value:
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


def parse_locality_from_text(text: str):
    # simple: grab "#### City" anywhere
    m = re.search(r"\b(\d{4})\s+([A-Za-zÀ-ÿ' -]+)\b", text)
    return m.group(2).strip() if m else None


def _maybe_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return extract_first_float(str(v))


def _maybe_int(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return extract_first_int(str(v))


def _find_jsonld(soup: BeautifulSoup) -> dict | None:
    """Return a JSON-LD blob that looks like a listing (if present)."""
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (s.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            if "offers" in cand or "address" in cand or cand.get("@type"):
                return cand
    return None


def _find_next_data(soup: BeautifulSoup) -> dict | None:
    s = soup.find("script", id="__NEXT_DATA__")
    raw = (s.string or "").strip() if s else ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _walk_find_listing(obj):
    """Best-effort recursive search for a dict that looks like a property."""
    if isinstance(obj, dict):
        keys = set(obj.keys())
        if {"price", "address"} <= keys or {"price", "zip"} <= keys or {"bedrooms", "price"} <= keys:
            return obj
        for v in obj.values():
            found = _walk_find_listing(v)
            if found:
                return found
    elif isinstance(obj, list):
        for it in obj:
            found = _walk_find_listing(it)
            if found:
                return found
    return None


def parse_detail(html: str, url: str, province: str, type_seed: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    # 1) structured sources (often present even when the visible blocks are rendered by JS)
    jsonld = _find_jsonld(soup)
    next_data = _find_next_data(soup)
    listing = _walk_find_listing(next_data) if next_data else None

    # 2) fallback DOM extraction
    kv = parse_h4_kv(soup)

    # ---- ID ----
    immovlan_id = parse_immovlan_id(text)
    if not immovlan_id:
        m = re.search(r"\bRB[A-Z]\d+\b", url.upper())
        immovlan_id = m.group(0) if m else None

    # ---- price ----
    price = None
    if jsonld and isinstance(jsonld.get("offers"), dict):
        price = _maybe_int(jsonld["offers"].get("price"))
    if price is None and listing:
        price = _maybe_int(listing.get("price") or listing.get("priceValue"))
    if price is None:
        price = normalize_price_from_text(text)

    # ---- locality ----
    locality = None
    if jsonld and isinstance(jsonld.get("address"), dict):
        locality = jsonld["address"].get("addressLocality") or jsonld["address"].get("addressRegion")
    if not locality and listing:
        addr = listing.get("address") if isinstance(listing.get("address"), dict) else {}
        locality = addr.get("locality") or addr.get("city") or listing.get("locality")
    if not locality:
        locality = parse_locality_from_text(text)

    # ---- subtype/type ----
    subtype = None
    if jsonld:
        st = jsonld.get("@type")
        if isinstance(st, str) and st.strip():
            subtype = st.strip()
    if not subtype and listing:
        for k in ("subtype", "propertySubType", "propertyType"):
            if listing.get(k):
                subtype = str(listing.get(k)).strip() or None
                break

    # ---- main numeric features ----
    bedrooms = None
    living_area = None
    land_surface = None
    plot_surface = None

    if jsonld:
        bedrooms = _maybe_int(jsonld.get("numberOfRooms") or jsonld.get("numberOfBedrooms"))
        floor = jsonld.get("floorSize")
        if isinstance(floor, dict):
            living_area = _maybe_float(floor.get("value"))
        land = jsonld.get("landSurface")
        if isinstance(land, dict):
            land_surface = _maybe_float(land.get("value"))

    if listing:
        bedrooms = bedrooms or _maybe_int(listing.get("bedrooms") or listing.get("roomCount"))
        living_area = living_area or _maybe_float(
            listing.get("livingArea")
            or listing.get("habitableSurface")
            or listing.get("livableSurface")
            or listing.get("surface")
        )
        land_surface = land_surface or _maybe_float(listing.get("landSurface") or listing.get("landArea"))
        plot_surface = plot_surface or _maybe_float(listing.get("plotSurface") or listing.get("plotArea"))

    # fallback to <h4> blocks
    bedrooms = bedrooms or extract_first_int(first_present(kv, "Number of bedrooms", "Bedrooms"))
    living_area = living_area or extract_first_float(
        first_present(kv, "Living area", "Livable surface", "Habitable surface")
    )
    land_surface = land_surface or extract_first_float(first_present(kv, "Total land surface", "Land surface"))
    plot_surface = plot_surface or extract_first_float(first_present(kv, "Plot surface", "Surface of the plot"))

    furnished = yesno_to_bin(first_present(kv, "Furnished"))
    terrace = yesno_to_bin(first_present(kv, "Terrace"))
    garden = yesno_to_bin(first_present(kv, "Garden"))
    facades = extract_first_int(first_present(kv, "Number of facades", "Number of frontages"))
    pool = yesno_to_bin(first_present(kv, "Swimming pool"))

    # kitchen equipped: heuristic
    kitchen_equipped = None
    ktxt = first_present(kv, "Kitchen equipment", "Equipped kitchen")
    if ktxt:
        t = ktxt.lower()
        kitchen_equipped = 1 if ("equipped" in t or "installed" in t or "fitted" in t) else 0

    building_state = first_present(kv, "State of the property", "Condition")

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
        "subtype": subtype,
        "sale_type": 0,
        "open_fire": None,
        "terrace_area_m2": None,
        "garden_area_m2": None,
        "plot_surface_m2": plot_surface,
    }