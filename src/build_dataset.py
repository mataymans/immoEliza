import pandas as pd
from src.utils import read_jsonl

IN_FILE = "data/raw_rows.jsonl"
OUT_FILE = "data/immovlan_clean.csv"

COLUMNS = [
    "locality",
    "property_type",      # house/apartment (string is ok; you can map later)
    "subtype",
    "price_eur",
    "sale_type",
    "bedrooms",
    "living_area_m2",
    "kitchen_equipped",
    "furnished",
    "open_fire",
    "terrace",
    "terrace_area_m2",
    "garden",
    "garden_area_m2",
    "land_surface_m2",
    "plot_surface_m2",
    "facades",
    "swimming_pool",
    "building_state",
    "province",
    "immovlan_id",
    "url",
]


def build_dataset():
    rows = list(read_jsonl(IN_FILE) or [])
    df = pd.DataFrame(rows)

    # ensure all columns exist
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None

    df = df[COLUMNS]

    # dedupe
    df = df.dropna(subset=["immovlan_id"])
    df = df.drop_duplicates(subset=["immovlan_id"], keep="first")

    # enforce numeric where expected
    for col in ["price_eur", "bedrooms", "facades"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in [
        "living_area_m2",
        "terrace_area_m2",
        "garden_area_m2",
        "land_surface_m2",
        "plot_surface_m2",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # booleans as 0/1 (nullable)
    for col in ["kitchen_equipped", "furnished", "open_fire", "terrace", "garden", "swimming_pool"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # “no empty row”: keep rows even if many None, but ensure at least id+url exist
    df = df.dropna(subset=["url", "immovlan_id"])

    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows -> {OUT_FILE}")


def main():
    build_dataset()


if __name__ == "__main__":
    main()