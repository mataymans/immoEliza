from src.collect_urls import collect_urls
from src.scrape_details import scrape_details
from src.build_dataset import build_dataset


def main():
    print("Step 1: Collecting URLs...")
    collect_urls(max_pages=50)

    print("Step 2: Scraping details...")
    scrape_details(max_workers=24)

    print("Step 3: Building dataset...")
    build_dataset()

    print("Done.")


if __name__ == "__main__":
    main()