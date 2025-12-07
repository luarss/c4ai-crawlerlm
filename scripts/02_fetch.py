"""Script to fetch web content using Exa API."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()


def load_urls(file_path: str) -> list[str]:
    """Load URLs from text file (one per line)."""
    urls = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)

    print(f"Loaded {len(urls)} URLs from {file_path}")
    return urls


def main():
    """Main execution function."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError(
            "EXA_API_KEY not found. Please set it in .env file or environment."
        )

    exa = Exa(api_key=api_key)

    # Load URLs
    urls = load_urls("data/selected_url_list.txt")

    if not urls:
        print("No URLs found to fetch.")
        return

    # Limit to 1 URL for testing
    urls = urls[:1]

    # Fetch content using Exa
    print(f"Fetching content for {len(urls)} URLs...")
    result = exa.get_contents(urls, text=True)

    # Save results
    output_dir = Path("data/fetched")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "exa_contents.json"

    # Convert results to clean structured JSON
    results_data = []
    for r in result.results:
        results_data.append({
            "url": r.url,
            "title": r.title,
            "text": r.text,
            "author": r.author,
            "published_date": r.published_date,
            "image": r.image,
            "favicon": r.favicon,
            "id": r.id,
        })

    with open(output_file, 'w') as f:
        json.dump(results_data, f, indent=2)

    print(f"\nFetch complete!")
    print(f"Saved {len(result.results)} results to {output_file}")


if __name__ == "__main__":
    main()
