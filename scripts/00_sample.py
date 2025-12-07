"""
Script to sample diverse URLs directly from Common Crawl index.

Common Crawl provides free access to web crawl data. This script samples
URLs from their index without needing to download WARC files.
"""

import json
import random
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
import time
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

random.seed(42)


def get_available_indexes() -> List[str]:
    """Get list of available Common Crawl indexes."""
    url = "https://index.commoncrawl.org/collinfo.json"
    response = httpx.get(url)
    response.raise_for_status()

    indexes = response.json()
    return [idx['id'] for idx in indexes]


def sample_urls_from_index(
    index_id: str,
    sample_size: int = 1000,
    domain_diversity: bool = True
) -> List[Dict]:
    """Sample URLs from a Common Crawl index."""
    base_url = f"https://index.commoncrawl.org/{index_id}-index"

    # Query patterns to get diverse content
    query_pattern = "*"

    params = {
        "url": query_pattern,
        "output": "json",
        "limit": sample_size * 3,
    }

    print(f"Querying Common Crawl index: {index_id}")
    print(f"Fetching URLs...")

    results = []
    seen_domains = set()

    try:
        # Stream response to process line-by-line without loading entire response into memory
        with httpx.stream('GET', base_url, params=params, timeout=60) as response:
            response.raise_for_status()

            for line in tqdm(response.iter_lines(), desc="Processing URLs"):
                if not line:
                    continue

                try:
                    record = json.loads(line)

                    # Filter for HTML content
                    mime = record.get('mime', '')
                    status = record.get('status', '')
                    url = record.get('url', '')

                    if 'text/html' not in mime or status != '200':
                        continue

                    # Extract domain for diversity
                    if domain_diversity:
                        domain = extract_domain(url)
                        if domain in seen_domains:
                            continue
                        seen_domains.add(domain)

                    results.append({
                        'url': url,
                        'timestamp': record.get('timestamp'),
                        'mime': mime,
                        'status': status,
                        'digest': record.get('digest'),
                    })

                    if len(results) >= sample_size:
                        break

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"Error querying Common Crawl: {e}")

    print(f"Sampled {len(results)} unique URLs")
    return results


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc


def fetch_and_validate_single_url(url_data: Dict, timeout: int = 10) -> tuple:
    """Fetch and validate a single URL."""
    url = url_data['url']

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)

            # Check status code
            if response.status_code != 200:
                return (False, url_data, None)

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return (False, url_data, None)

            # Check minimum content length
            if len(response.text) < 500:
                return (False, url_data, None)

            # Check for HTML tags
            html_lower = response.text.lower()
            if '<html' not in html_lower and '<body' not in html_lower:
                return (False, url_data, None)

            return (True, url_data, response.text)

    except Exception:
        return (False, url_data, None)


def validate_and_save_urls(urls: List[Dict], output_dir: Path, max_workers: int = 10) -> List[Dict]:
    """Validate URLs, fetch HTML, and save directly to disk (parallelized)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nValidating and fetching {len(urls)} URLs with {max_workers} workers...")

    # Pre-assign IDs to URLs for consistent filename mapping
    url_data_with_id = []
    for idx, url_data in enumerate(urls):
        url_data_copy = url_data.copy()
        url_data_copy['assigned_id'] = idx
        url_data_with_id.append(url_data_copy)

    # Use ThreadPoolExecutor for parallel fetching
    results = {}  # Store by assigned_id
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(fetch_and_validate_single_url, url_data): url_data
            for url_data in url_data_with_id
        }

        # Process completed tasks with progress bar
        for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Fetching & saving HTML"):
            success, url_data, html_content = future.result()

            if success and html_content:
                assigned_id = url_data['assigned_id']

                # Save HTML to file using assigned ID (not completion order)
                html_file = output_dir / f"{assigned_id:04d}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_content)

                # Store result
                results[assigned_id] = {
                    "id": assigned_id,
                    "url": url_data['url'],
                    "domain": url_data.get('domain', ''),
                    "category": url_data.get('category', ''),
                    "html_file": str(html_file),
                    "timestamp": url_data.get('timestamp', ''),
                }

    # Convert to sorted list
    valid_urls = [results[id] for id in sorted(results.keys())]

    print(f"✓ {len(valid_urls)} URLs fetched and saved ({len(urls) - len(valid_urls)} failed)")
    return valid_urls


def sample_by_category(index_id: str, urls_per_category: int = 10) -> List[Dict]:
    """Sample URLs from different categories/domains with domain deduplication."""
    # Different domain patterns to ensure diversity
    patterns = [
        "*.edu/*",      # Educational
        "*.org/*",      # Organizations
        "*.gov/*",      # Government
        "*.com/*",      # Commercial
        "*.io/*",       # Tech
        "*.net/*",      # Networks
    ]

    all_results = []
    base_url = f"https://index.commoncrawl.org/{index_id}-index"

    for pattern in tqdm(patterns, desc="Sampling categories"):
        params = {
            "url": pattern,
            "output": "json",
            "limit": urls_per_category * 50,  # Fetch many more for random sampling
        }

        try:
            response = httpx.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            # Collect all candidates first
            candidates = []
            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    record = json.loads(line)

                    # Filter for HTML
                    if 'text/html' in record.get('mime', '') and record.get('status') == '200':
                        url = record.get('url')
                        domain = extract_domain(url)

                        candidates.append({
                            'url': url,
                            'domain': domain,
                            'category': pattern,
                            'timestamp': record.get('timestamp'),
                        })

                except json.JSONDecodeError:
                    continue

            # Randomly shuffle candidates
            random.shuffle(candidates)

            # Pick unique domains
            category_results = []
            seen_domains = set()

            for candidate in candidates:
                domain = candidate['domain']

                if domain in seen_domains:
                    continue

                seen_domains.add(domain)
                category_results.append(candidate)

                if len(category_results) >= urls_per_category:
                    break

            print(f"  {pattern}: {len(category_results)} unique domains")
            all_results.extend(category_results)
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"Error fetching {pattern}: {e}")
            continue

    # Shuffle for more randomness
    random.shuffle(all_results)
    return all_results


def main():
    """Main execution function."""
    # Get latest index
    print("Fetching available Common Crawl indexes...")
    indexes = get_available_indexes()
    latest_index = indexes[0]

    print(f"Using index: {latest_index}")
    print(f"Available indexes: {len(indexes)}")

    # Output directory for HTML files
    html_output_dir = Path("data/raw_html")

    # Sample diverse URLs (fetch extra to account for validation failures)
    sampled_urls = sample_by_category(
        index_id=latest_index,
        urls_per_category=75
    )

    # Validate and save URLs directly to data/raw_html
    valid_urls = validate_and_save_urls(sampled_urls, html_output_dir)

    # If we need more valid URLs, sample again
    target_count = 400
    if len(valid_urls) < target_count:
        print(f"\nNeed {target_count - len(valid_urls)} more valid URLs...")
        additional = sample_by_category(
            index_id=latest_index,
            urls_per_category=50
        )
        more_valid = validate_and_save_urls(additional, html_output_dir)
        valid_urls.extend(more_valid)

    final_urls = valid_urls

    # Save manifest
    manifest_file = html_output_dir / "dataset_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(final_urls, f, indent=2)

    print(f"\n✓ Final dataset: {len(final_urls)} HTML files saved")
    print(f"✓ HTML files: {html_output_dir}")
    print(f"✓ Manifest: {manifest_file}")
    print("\nReady for training! HTML files are in data/raw_html/")


if __name__ == "__main__":
    main()
