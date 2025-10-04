import requests
import pandas as pd
from bs4 import BeautifulSoup
import logging
import json
import argparse

# Basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. Load the CSV with titles and links
try:
    df = pd.read_csv("SB_publication_PMC.csv").head(10) # TODO: Change to full dataset after testing
    logging.info(f"CSV successfully loaded. Found {len(df)} publications.")
except FileNotFoundError:
    logging.error("Error: 'SB_publication_PMC.csv' file not found. Please ensure it is in the same folder as the script.")
    exit()

# 2. Function to scrape an article
def scrape_article(url):
    data = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logging.error(f"No se pudo acceder a {url}. Status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.select_one("hgroup")

        #pmc_id
        pmc_id = url.rstrip("/").split("/")[-1]
        data["pmc_id"] = pmc_id
        
        # Title
        data["title"] = title.get_text(strip=True) if title else None

        # Authors
        authors = []
        author_container = soup.select_one("div.cg.p")
        if author_container:
            try:
                visible_spans = author_container.select(":scope > a > span.name.western")
            except Exception:
                visible_spans = [s for s in author_container.select("a > span.name.western") if s.find_parent("div", hidden=True) is None]

            seen = set()
            for span in visible_spans:
                name = span.get_text(strip=True)
                if name and name not in seen:
                    seen.add(name)
                    authors.append(name)

        data["authors"] = authors
        logging.info(f"Authors found (deduped): {authors}")

        # Journal

        # Publication Date

        # Abstract

        # Sections

        # Go through each of the sections and extract text



        # References

        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"Internet error while trying to access {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while processing {url}: {e}")
        return None


# 3. Iterate over the CSV and extract data
articles_data = []

# Check if the required columns exist
if "Link" not in df.columns or "Title" not in df.columns:
    logging.error("The CSV must have 'Title' and 'Link' columns. Please check the file.")
    exit()

# Iterate over rows
for idx, row in df.iterrows():
    url = row["Link"]
    title = row["Title"]
    
    if not isinstance(url, str) or not url.startswith('http'):
        logging.warning(f"Row {idx+1} skipped: Invalid URL ('{url}') for title '{title}'")
        continue

    logging.info(f"Processing {idx+1}/{len(df)}: '{title}'")
    article_info = scrape_article(url)
    
    if article_info:
        # Add the original URL for reference
        article_info['source_url'] = url
        articles_data.append(article_info)

def save_results(data, output_format):
    if not data:
        logging.warning("No articles could be extracted. No output generated.")
        return

    # Normalized file base name
    base_name = "space_biology_scraped"

    if output_format in ("csv", "both"):
        df_out = pd.DataFrame(data)
        df_out.to_csv(f"{base_name}.csv", index=False)
        logging.info(f"CSV written: {base_name}.csv ({len(df_out)} rows)")

    if output_format in ("json", "both"):
        # Ensure UTF-8 and readable formatting; preserve lists
        with open(f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"JSON written: {base_name}.json ({len(data)} objects)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Space Biology publications scraper")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="csv", help="Output format (default: csv)")
    args = parser.parse_args()

    save_results(articles_data, args.format)
