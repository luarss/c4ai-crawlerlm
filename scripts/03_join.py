"""Script to join HTML files with JSON extracts into JSONL format.

This script combines:
- HTML files from data/raw_html_backup_100/
- JSON extracts from data/fetched/exa_contents.json
- Metadata from data/raw_html_backup_100/dataset_manifest.json

Output format:
{
    "example_html": "<html>...</html>",
    "expected_json": {"url": "...", "title": "...", "text": "..."}
}
"""

import json
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse


def load_manifest(manifest_path: str) -> Dict[str, dict]:
    """Load manifest and create URL to metadata mapping."""
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    url_to_entry = {entry['url']: entry for entry in manifest}
    print(f"Loaded {len(url_to_entry)} entries from manifest")
    return url_to_entry


def normalize_url(url: str) -> str:
    """Normalize URL for matching (remove trailing slash, lowercase domain)."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    normalized = f"{domain}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def load_exa_contents(exa_path: str) -> Dict[str, dict]:
    """Load Exa JSON extracts and create URL mapping."""
    with open(exa_path, 'r') as f:
        exa_contents = json.load(f)

    url_to_json = {}
    for entry in exa_contents:
        url_to_json[entry['url']] = entry
        url_to_json[normalize_url(entry['url'])] = entry

    print(f"Loaded {len(exa_contents)} JSON extracts from Exa")
    return url_to_json


def read_html_file(html_path: Path) -> str:
    """Read HTML file content."""
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def join_datasets(manifest_path: str, exa_path: str, output_path: str):
    """Join HTML files with JSON extracts using the original manifest."""
    url_to_manifest = load_manifest(manifest_path)

    with open(exa_path, 'r') as f:
        exa_contents = json.load(f)

    print(f"Loaded {len(url_to_manifest)} entries from manifest")
    print(f"Loaded {len(exa_contents)} JSON extracts from Exa")

    joined_data = []
    found_count = 0
    not_found_urls = []

    for exa_entry in exa_contents:
        exa_url = exa_entry['url']

        manifest_entry = url_to_manifest.get(exa_url)

        if not manifest_entry:
            for url_variant in [exa_url, exa_url.replace('://', '://www.'), exa_url.replace('://www.', '://')]:
                for url_slash in [url_variant, url_variant.rstrip('/'), url_variant + '/']:
                    for url_scheme in [url_slash, url_slash.replace('https://', 'http://'), url_slash.replace('http://', 'https://')]:
                        if url_scheme in url_to_manifest:
                            manifest_entry = url_to_manifest[url_scheme]
                            break
                    if manifest_entry:
                        break
                if manifest_entry:
                    break

        if manifest_entry:
            html_file = manifest_entry['html_file']
            html_path = Path(html_file)

            try:
                html_content = read_html_file(html_path)

                joined_entry = {
                    "example_html": html_content,
                    "expected_json": exa_entry
                }
                joined_data.append(joined_entry)
                found_count += 1

            except FileNotFoundError:
                print(f"Warning: HTML file not found: {html_path} for URL: {exa_url}")
                not_found_urls.append(exa_url)
        else:
            not_found_urls.append(exa_url)

    print(f"\nDataset statistics:")
    print(f"  Exa JSON extracts: {len(exa_contents)}")
    print(f"  Successfully matched and joined: {found_count}")
    print(f"  Not found in manifest: {len(not_found_urls)}")

    if not_found_urls:
        print(f"\nURLs not found in manifest:")
        for url in not_found_urls[:5]:
            print(f"  {url}")
        if len(not_found_urls) > 5:
            print(f"  ... and {len(not_found_urls) - 5} more")

    # Save to JSONL
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in joined_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"\nJoined dataset saved to: {output_file}")
    print(f"Total entries: {len(joined_data)}")

    if joined_data:
        print("\nSample entry structure:")
        sample = joined_data[0]
        print(f"  example_html length: {len(sample['example_html'])} characters")
        print(f"  expected_json keys: {list(sample['expected_json'].keys())}")
        print(f"  URL: {sample['expected_json']['url']}")


def main():
    """Main execution function."""
    manifest_path = "data/raw_html/dataset_manifest.json"
    exa_path = "data/fetched/exa_contents.json"
    output_path = "data/processed/golden.jsonl"

    print("Joining HTML files with JSON extracts...")
    join_datasets(manifest_path, exa_path, output_path)
    print("\nDone!")


if __name__ == "__main__":
    main()
