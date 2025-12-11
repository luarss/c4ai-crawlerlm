"""Script to fetch web content using Exa API."""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from exa_py import Exa
from tqdm import tqdm

load_dotenv()

NUM_WORKERS = 5


def load_urls(file_path: str) -> list[str]:
    """Load URLs from text file (one per line)."""
    urls = []
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line and line.startswith("http"):
                urls.append(line)

    print(f"Loaded {len(urls)} URLs from {file_path}")
    return urls


def fetch_batch(exa: Exa, batch_urls: list[str]) -> tuple[list[dict], float]:
    """Fetch a batch of URLs using Exa API."""
    result = exa.get_contents(batch_urls, text=True)

    batch_data = []
    for r in result.results:
        batch_data.append(
            {
                "url": r.url,
                "title": r.title,
                "text": r.text,
                "author": r.author,
                "published_date": r.published_date,
                "image": r.image,
                "favicon": r.favicon,
                "id": r.id,
            }
        )

    # Extract cost from result
    cost = result.cost_dollars.total if hasattr(result, "cost_dollars") else 0.0
    return batch_data, cost


def main():
    """Main execution function."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY not found. Please set it in .env file or environment.")

    exa = Exa(api_key=api_key)

    # Load URLs
    urls = load_urls("data/selected_url_list.txt")

    if not urls:
        print("No URLs found to fetch.")
        return

    # Split URLs into batches for parallel processing
    batch_size = max(1, len(urls) // NUM_WORKERS)
    batches = [urls[i : i + batch_size] for i in range(0, len(urls), batch_size)]

    print(f"Fetching content for {len(urls)} URLs using {NUM_WORKERS} workers...")
    print(f"Processing {len(batches)} batches")

    # Fetch content in parallel
    results_data = []
    total_cost = 0.0
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(fetch_batch, exa, batch) for batch in batches]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching batches"):
            batch_results, batch_cost = future.result()
            results_data.extend(batch_results)
            total_cost += batch_cost

    # Save results
    output_dir = Path("data/fetched")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "exa_contents.json"

    with open(output_file, "w") as f:
        json.dump(results_data, f, indent=2)

    print("\nFetch complete!")
    print(f"Saved {len(results_data)} results to {output_file}")
    print(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
