"""
Select the best 50 URLs for training based on quality criteria.

Criteria:
1. Static/SSR pages (not dynamic/SPA)
2. No anomalies (errors, redirects, captchas, etc.)
3. Good content quality (sufficient text, reasonable size)
4. Token count within reasonable range (4K-128K tokens)
"""

import json
from pathlib import Path
from bs4 import BeautifulSoup
import re
from typing import Dict, List
import tiktoken


def detect_spa_or_dynamic(html: str, soup: BeautifulSoup) -> bool:
    """Return True if page is SPA or heavily dynamic."""
    # Check for common SPA frameworks
    if re.search(r'react|__NEXT_DATA__|_reactRoot|data-reactroot|vue\.js|__NUXT__|ng-app|angular\.js|svelte', html, re.I):
        return True

    # Check for minimal text with root div
    root_divs = soup.find_all('div', id=re.compile(r'^(root|app|__next)$', re.I))
    if root_divs and len(soup.get_text(strip=True)) < 500:
        return True

    # Check text-to-html ratio
    text_content = soup.get_text(strip=True)
    text_ratio = len(text_content) / len(html) if len(html) > 0 else 0

    # Check for loading indicators
    loading_indicators = bool(re.search(
        r'loading|please wait|enabling javascript|javascript is required',
        text_content[:1000], re.I
    ))

    script_tags = soup.find_all('script')
    if len(script_tags) > 10 and text_ratio < 0.1:
        return True

    return loading_indicators


def has_anomalies(html: str, soup: BeautifulSoup) -> bool:
    """Return True if page has anomalies."""
    text_content = soup.get_text(strip=True).lower()

    # Empty page
    if len(text_content) < 100:
        return True

    # Error pages
    error_patterns = [
        r'404|not found', r'403|forbidden', r'500|internal server error',
        r'502|bad gateway', r'503|service unavailable', r'error occurred'
    ]
    for pattern in error_patterns:
        if re.search(pattern, text_content):
            return True

    # Redirects
    if re.search(r'redirect|redirecting|you will be redirected', text_content):
        return True

    # Login required
    if re.search(r'login|sign in|authentication required|please log in', text_content[:500]):
        return True

    # Captcha
    if re.search(r'captcha|recaptcha|verify you are human|security check', text_content):
        return True

    # Robots blocked
    if re.search(r'robot|bot|crawler|automated access|rate limit', text_content[:1000]):
        return True

    # Malformed HTML
    if not soup.find('html') or not soup.find('body'):
        return True

    return False


def score_content_quality(html: str, soup: BeautifulSoup) -> float:
    """Score content quality (0-100)."""
    score = 0.0

    text_content = soup.get_text(separator=' ', strip=True)
    words = text_content.split()
    word_count = len(words)

    # Word count scoring (target: 500-5000 words)
    if 500 <= word_count <= 5000:
        score += 30
    elif 200 <= word_count < 500:
        score += 20
    elif 100 <= word_count < 200:
        score += 10

    # Vocabulary richness
    if word_count > 0:
        unique_words = len(set(w.lower() for w in words if len(w) > 3))
        vocab_richness = unique_words / word_count
        score += min(vocab_richness * 100, 20)  # Max 20 points

    # Semantic HTML elements
    semantic_tags = ['article', 'section', 'nav', 'header', 'footer', 'main', 'aside']
    semantic_count = sum(len(soup.find_all(tag)) for tag in semantic_tags)
    score += min(semantic_count * 2, 15)  # Max 15 points

    # Headers
    header_count = len(soup.find_all(re.compile(r'^h[1-6]$')))
    score += min(header_count * 1.5, 10)  # Max 10 points

    # Paragraphs
    p_count = len(soup.find_all('p'))
    score += min(p_count * 0.5, 10)  # Max 10 points

    # Links (not too many, not too few)
    links = soup.find_all('a', href=True)
    link_count = len(links)
    if 5 <= link_count <= 50:
        score += 10
    elif 2 <= link_count < 5 or 50 < link_count <= 100:
        score += 5

    # Meta tags
    meta_tags = soup.find_all('meta')
    has_description = any(m.get('name') == 'description' for m in meta_tags)
    has_viewport = any(m.get('name') == 'viewport' for m in meta_tags)
    if has_description:
        score += 2.5
    if has_viewport:
        score += 2.5

    return min(score, 100.0)


def analyze_url(html_path: Path, manifest_entry: Dict, encoding) -> Dict:
    """Analyze a single URL and return scoring metrics."""
    try:
        with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
            html = f.read()
    except Exception as e:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Filter criteria
    is_dynamic = detect_spa_or_dynamic(html, soup)
    has_issues = has_anomalies(html, soup)

    # Token count
    tokens = encoding.encode(html)
    token_count = len(tokens)

    # Score
    quality_score = score_content_quality(html, soup)

    return {
        'id': manifest_entry['id'],
        'url': manifest_entry['url'],
        'domain': manifest_entry['domain'],
        'category': manifest_entry['category'],
        'html_file': manifest_entry['html_file'],
        'is_dynamic': is_dynamic,
        'has_issues': has_issues,
        'token_count': token_count,
        'file_size': len(html),
        'quality_score': quality_score,
        'eligible': not is_dynamic and not has_issues and 4096 <= token_count <= 131072,
    }


def select_best_urls(manifest_path: Path, top_n: int = 50) -> List[Dict]:
    """Select the best N URLs based on quality criteria."""
    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Analyzing {len(manifest)} URLs...")

    # Initialize tokenizer
    encoding = tiktoken.get_encoding('cl100k_base')

    # Analyze all URLs
    results = []
    for entry in manifest:
        html_path = Path(entry['html_file'])
        result = analyze_url(html_path, entry, encoding)
        if result:
            results.append(result)

    print(f"Total analyzed: {len(results)}")

    # Filter eligible URLs
    eligible = [r for r in results if r['eligible']]
    print(f"Eligible URLs (static, no issues, 4K-128K tokens): {len(eligible)}")

    # Sort by quality score
    eligible_sorted = sorted(eligible, key=lambda x: x['quality_score'], reverse=True)

    # Select top N
    selected = eligible_sorted[:top_n]

    print(f"\nSelected top {len(selected)} URLs")
    print(f"Quality score range: {selected[-1]['quality_score']:.1f} - {selected[0]['quality_score']:.1f}")
    print(f"Token count range: {min(s['token_count'] for s in selected):,} - {max(s['token_count'] for s in selected):,}")

    # Category distribution
    from collections import Counter
    category_dist = Counter(s['category'] for s in selected)
    print(f"\nCategory distribution:")
    for cat, count in category_dist.items():
        print(f"  {cat}: {count}")

    return selected


def main():
    """Main execution."""
    manifest_path = Path("data/raw_html/dataset_manifest.json")

    # Select best 50 URLs
    selected_urls = select_best_urls(manifest_path, top_n=50)
    url_list_path = Path("data/selected_url_list.txt")
    with open(url_list_path, 'w') as f:
        for item in selected_urls:
            f.write(f"{item['url']}\n")

    print(f"✓ Saved URL list to: {url_list_path}")


if __name__ == "__main__":
    main()
