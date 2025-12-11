"""
Script to sample diverse URLs directly from Common Crawl index.

Common Crawl provides free access to web crawl data. This script samples
URLs from their index without needing to download WARC files.
"""

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx
from tqdm import tqdm

random.seed(42)


def get_available_indexes() -> list[str]:
    """Get list of available Common Crawl indexes."""
    url = "https://index.commoncrawl.org/collinfo.json"
    response = httpx.get(url)
    response.raise_for_status()

    indexes = response.json()
    return [idx["id"] for idx in indexes]


def sample_urls_from_index(index_id: str, sample_size: int = 1000, domain_diversity: bool = True) -> list[dict]:
    """Sample URLs from a Common Crawl index."""
    base_url = f"https://index.commoncrawl.org/{index_id}-index"

    query_pattern = "*"

    params = {
        "url": query_pattern,
        "output": "json",
        "limit": sample_size * 3,
    }

    print(f"Querying Common Crawl index: {index_id}")
    print("Fetching URLs...")

    results = []
    seen_domains = set()

    try:
        # Stream response to process line-by-line without loading entire response into memory
        with httpx.stream("GET", base_url, params=params, timeout=60) as response:
            response.raise_for_status()

            for line in tqdm(response.iter_lines(), desc="Processing URLs"):
                if not line:
                    continue

                try:
                    record = json.loads(line)

                    mime = record.get("mime", "")
                    status = record.get("status", "")
                    url = record.get("url", "")

                    if "text/html" not in mime or status != "200":
                        continue

                    if domain_diversity:
                        domain = extract_domain(url)
                        if domain in seen_domains:
                            continue
                        seen_domains.add(domain)

                    results.append(
                        {
                            "url": url,
                            "timestamp": record.get("timestamp"),
                            "mime": mime,
                            "status": status,
                            "digest": record.get("digest"),
                        }
                    )

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
    return urlparse(url).netloc


def fetch_and_validate_single_url(url_data: dict, timeout: int = 10) -> tuple:
    """Fetch and validate a single URL."""
    url = url_data["url"]

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)

            if response.status_code != 200:
                return (False, url_data, None)

            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return (False, url_data, None)

            if len(response.text) < 500:
                return (False, url_data, None)

            html_lower = response.text.lower()
            if "<html" not in html_lower and "<body" not in html_lower:
                return (False, url_data, None)

            return (True, url_data, response.text)

    except Exception:
        return (False, url_data, None)


def validate_and_save_urls(urls: list[dict], output_dir: Path, max_workers: int = 10) -> list[dict]:
    """Validate URLs, fetch HTML, and save directly to disk (parallelized)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nValidating and fetching {len(urls)} URLs with {max_workers} workers...")

    # Pre-assign IDs to URLs for consistent filename mapping
    url_data_with_id = []
    for idx, url_data in enumerate(urls):
        url_data_copy = url_data.copy()
        url_data_copy["assigned_id"] = idx
        url_data_with_id.append(url_data_copy)

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(fetch_and_validate_single_url, url_data): url_data for url_data in url_data_with_id
        }

        for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Fetching & saving HTML"):
            success, url_data, html_content = future.result()

            if success and html_content:
                assigned_id = url_data["assigned_id"]

                html_file = output_dir / f"{assigned_id:04d}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html_content)

                results[assigned_id] = {
                    "id": assigned_id,
                    "url": url_data["url"],
                    "domain": url_data.get("domain", ""),
                    "category": url_data.get("category", ""),
                    "html_file": str(html_file),
                    "timestamp": url_data.get("timestamp", ""),
                }

    valid_urls = [results[id] for id in sorted(results.keys())]

    print(f"✓ {len(valid_urls)} URLs fetched and saved ({len(urls) - len(valid_urls)} failed)")
    return valid_urls


def sample_by_category(index_id: str, urls_per_category: int = 10) -> list[dict]:
    """Sample URLs from different categories/domains with domain deduplication."""
    patterns = [
        "*.edu/*",
        "*.org/*",
        "*.gov/*",
        "*.com/*",
        "*.io/*",
        "*.net/*",
    ]

    all_results = []
    base_url = f"https://index.commoncrawl.org/{index_id}-index"

    for pattern in tqdm(patterns, desc="Sampling categories"):
        params = {
            "url": pattern,
            "output": "json",
            "limit": urls_per_category * 50,
        }

        try:
            response = httpx.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            candidates = []
            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    record = json.loads(line)

                    if "text/html" in record.get("mime", "") and record.get("status") == "200":
                        url = record.get("url")
                        domain = extract_domain(url)

                        candidates.append(
                            {
                                "url": url,
                                "domain": domain,
                                "category": pattern,
                                "timestamp": record.get("timestamp"),
                            }
                        )

                except json.JSONDecodeError:
                    continue

            random.shuffle(candidates)

            category_results = []
            seen_domains = set()

            for candidate in candidates:
                domain = candidate["domain"]

                if domain in seen_domains:
                    continue

                seen_domains.add(domain)
                category_results.append(candidate)

                if len(category_results) >= urls_per_category:
                    break

            print(f"  {pattern}: {len(category_results)} unique domains")
            all_results.extend(category_results)
            time.sleep(0.5)

        except Exception as e:
            print(f"Error fetching {pattern}: {e}")
            continue

    random.shuffle(all_results)
    return all_results


def main():
    """Main execution function."""
    print("Fetching available Common Crawl indexes...")
    indexes = get_available_indexes()
    latest_index = indexes[0]

    print(f"Using index: {latest_index}")
    print(f"Available indexes: {len(indexes)}")

    html_output_dir = Path("data/raw_html")

    sampled_urls = sample_by_category(index_id=latest_index, urls_per_category=150)

    valid_urls = validate_and_save_urls(sampled_urls, html_output_dir)

    target_count = 800
    if len(valid_urls) < target_count:
        print(f"\nNeed {target_count - len(valid_urls)} more valid URLs...")

        seen_domains = {url_data["domain"] for url_data in valid_urls}

        additional = sample_by_category(index_id=latest_index, urls_per_category=50)

        additional_filtered = [url_data for url_data in additional if url_data["domain"] not in seen_domains]

        print(f"Filtered {len(additional) - len(additional_filtered)} duplicate domains")

        more_valid = validate_and_save_urls(additional_filtered, html_output_dir)
        valid_urls.extend(more_valid)

    seen_urls = set()
    final_urls = []
    duplicates_removed = 0

    for url_data in valid_urls:
        url = url_data["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            final_urls.append(url_data)
        else:
            duplicates_removed += 1

    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate URLs in final deduplication")

    valid_urls = final_urls

    manifest_file = html_output_dir / "dataset_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(final_urls, f, indent=2)

    print(f"\n✓ Final dataset: {len(final_urls)} HTML files saved")
    print(f"✓ HTML files: {html_output_dir}")
    print(f"✓ Manifest: {manifest_file}")
    print("\nReady for training! HTML files are in data/raw_html/")


if __name__ == "__main__":
    main()
