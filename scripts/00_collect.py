import argparse
import asyncio
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import (
    AsyncUrlSeeder,
    AsyncWebCrawler,
    BFSDeepCrawlStrategy,
    CrawlerRunConfig,
    FilterChain,
    SeedingConfig,
    URLPatternFilter,
)

from src.schemas import get_schema


class FragmentCollector:
    """Collect fragment candidates from domains using Crawl4AI URL seeding."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.candidates_dir = project_root / "data" / "seeds" / "candidates"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        self.negatives_dir = project_root / "data" / "seeds" / "negatives"
        self.negatives_dir.mkdir(parents=True, exist_ok=True)

        # Domain-based configuration for auto-discovery
        # Each domain has pattern, query, and target count
        # Includes configs that deliberately collect negative examples (auth walls, SPAs, errors)
        self.domain_configs = {
            "recipe": [
                {
                    "domain": "allrecipes.com",
                    "pattern": "*/recipe/*",
                    "max_urls": 25,
                },
                {
                    "domain": "bbcgoodfood.com",
                    "pattern": "*/recipes/*",
                    "max_urls": 25,
                },
                {
                    "domain": "loveandlemons.com",
                    "pattern": "*-recipe*/",
                    "max_urls": 25,
                },
                {
                    "domain": "seriouseats.com",
                    "pattern": "*recipe*",
                    "max_urls": 25,
                },
            ],
            "product": [
                {
                    "domain": "wirecutter.com",
                    "pattern": "*/reviews/*",
                    "max_urls": 30,
                },
                {
                    "domain": "thespruce.com",
                    "pattern": "*/best-*",
                    "max_urls": 30,
                },
                {
                    "domain": "pcmag.com",
                    "pattern": "*/reviews/*",
                    "max_urls": 30,
                },
                {
                    "domain": "techradar.com",
                    "pattern": "*/reviews/*",
                    "max_urls": 30,
                },
                {
                    "domain": "tomsguide.com",
                    "pattern": "*/reviews/*",
                    "max_urls": 30,
                },
                {
                    "domain": "cnet.com",
                    "pattern": "*/products/*",
                    "max_urls": 30,
                },
                {
                    "domain": "engadget.com",
                    "pattern": "*/*",
                    "max_urls": 30,
                },
                {
                    "domain": "theverge.com",
                    "pattern": "*/*",
                    "max_urls": 30,
                },
            ],
            "event": [
                {
                    "domain": "meetup.com",
                    "pattern": "*/events/*",
                    "max_urls": 25,
                },
                {
                    "domain": "eventbrite.com",
                    "pattern": "*/e/*",
                    "max_urls": 25,
                },
                {
                    "domain": "events.cornell.edu",
                    "pattern": "*/event/*",
                    "max_urls": 20,
                },
                {
                    "domain": "lu.ma",
                    "pattern": "*/*",
                    "max_urls": 20,
                },
            ],
            "pricing_table": [
                {
                    "domain": "stripe.com",
                    "pattern": "*/pricing*",
                    "max_urls": 15,
                },
                {
                    "domain": "notion.so",
                    "pattern": "*/pricing*",
                    "max_urls": 15,
                },
                {
                    "domain": "airtable.com",
                    "pattern": "*/pricing*",
                    "max_urls": 15,
                },
                {
                    "domain": "mongodb.com",
                    "pattern": "*/pricing*",
                    "max_urls": 15,
                },
                {
                    "domain": "shopify.com",
                    "pattern": "*/pricing*",
                    "max_urls": 15,
                },
                {
                    "domain": "hubspot.com",
                    "pattern": "*/pricing*",
                    "max_urls": 15,
                },
            ],
            "job_posting": [
                # Job board aggregators
                {
                    "domain": "jobs.lever.co",
                    "pattern": "*/*",
                    "max_urls": 50,
                },
                {
                    "domain": "boards.greenhouse.io",
                    "pattern": "*/*",
                    "max_urls": 50,
                },
                {
                    "domain": "job-boards.greenhouse.io",
                    "pattern": "*/*",
                    "max_urls": 50,
                },
                # Remote job boards (tend to have clean HTML)
                {
                    "domain": "remoteok.com",
                    "pattern": "*/remote-jobs/*",
                    "max_urls": 50,
                },
                {
                    "domain": "weworkremotely.com",
                    "pattern": "*/remote-jobs/*",
                    "max_urls": 50,
                },
                {
                    "domain": "remote.co",
                    "pattern": "*/remote-jobs/*",
                    "max_urls": 50,
                },
                # Startup job boards
                {
                    "domain": "wellfound.com",
                    "pattern": "*/jobs/*",
                    "max_urls": 50,
                },
                {
                    "domain": "ycombinator.com",
                    "pattern": "*/jobs/*",
                    "max_urls": 30,
                },
                # Company career pages (keep existing)
                {
                    "domain": "stripe.com",
                    "pattern": "*/jobs/*",
                    "max_urls": 30,
                },
                {
                    "domain": "anthropic.com",
                    "pattern": "*/careers*",
                    "max_urls": 30,
                },
                # Tech company career pages
                {
                    "domain": "openai.com",
                    "pattern": "*/careers/*",
                    "max_urls": 30,
                },
                {
                    "domain": "google.com",
                    "pattern": "*/careers/*",
                    "max_urls": 30,
                },
            ],
            "person": [
                {
                    "domain": "stanford.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                {
                    "domain": "mit.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                {
                    "domain": "berkeley.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
            ],
            # Negative collectors - sites likely to produce auth walls, paywalls, SPAs
            "paywall_content": [
                {
                    "domain": "nytimes.com",
                    "pattern": "*/article/*",
                    "max_urls": 20,
                },
                {
                    "domain": "wsj.com",
                    "pattern": "*/articles/*",
                    "max_urls": 20,
                },
                {
                    "domain": "ft.com",
                    "pattern": "*/content/*",
                    "max_urls": 20,
                },
                {
                    "domain": "economist.com",
                    "pattern": "*/article/*",
                    "max_urls": 20,
                },
                {
                    "domain": "medium.com",
                    "pattern": "*/*",
                    "max_urls": 20,
                },
            ],
            "spa_heavy": [
                # Modern SPA frameworks - likely to have minimal server-rendered content
                {
                    "domain": "netflix.com",
                    "pattern": "*/title/*",
                    "max_urls": 15,
                },
                {
                    "domain": "spotify.com",
                    "pattern": "*/playlist/*",
                    "max_urls": 15,
                },
                {
                    "domain": "figma.com",
                    "pattern": "*/file/*",
                    "max_urls": 15,
                },
                {
                    "domain": "notion.so",
                    "pattern": "*/*",
                    "max_urls": 15,
                },
            ],
            "authrequired": [
                # Use deep crawling to find login/signin pages from main pages
                {
                    "seed_url": "https://github.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://gitlab.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://www.linkedin.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://medium.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://twitter.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://www.reddit.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://www.instagram.com",
                    "max_pages": 10,
                },
                {
                    "seed_url": "https://www.pinterest.com",
                    "max_pages": 10,
                },
            ],
            "error_page": [
                # Various domains to collect diverse error pages
                # Using likely-404 paths to trigger error pages
                {
                    "domain": "github.com",
                    "pattern": "*/nonexistent-*",
                    "max_urls": 10,
                },
                {
                    "domain": "stackoverflow.com",
                    "pattern": "*/questions/99999999/*",
                    "max_urls": 10,
                },
                {
                    "domain": "reddit.com",
                    "pattern": "*/r/nonexistent*",
                    "max_urls": 10,
                },
                {
                    "domain": "medium.com",
                    "pattern": "*/deleted-*",
                    "max_urls": 10,
                },
                {
                    "domain": "twitter.com",
                    "pattern": "*/status/999999999*",
                    "max_urls": 10,
                },
                {
                    "domain": "youtube.com",
                    "pattern": "*/watch?v=deleted*",
                    "max_urls": 10,
                },
                {
                    "domain": "amazon.com",
                    "pattern": "*/dp/INVALID*",
                    "max_urls": 10,
                },
                {
                    "domain": "stripe.com",
                    "pattern": "*/docs/nonexistent*",
                    "max_urls": 10,
                },
            ],
        }

    def _get_fragment_id(self, html: str) -> str:
        """Generate unique ID for fragment."""
        return hashlib.md5(html.encode()).hexdigest()[:8]

    async def discover_urls(self, fragment_type: str) -> dict[str, list[str]]:
        """
        Discover URLs from domain sitemaps using AsyncUrlSeeder.

        Returns:
            dict mapping domain to list of discovered URLs
        """
        domain_configs = self.domain_configs.get(fragment_type, [])
        if not domain_configs:
            print(f"No domain configurations for type: {fragment_type}")
            return {}

        print(f"\n🔍 Discovering {fragment_type} URLs from {len(domain_configs)} domains...")
        print("-" * 70)

        discovered_urls = {}

        async with AsyncUrlSeeder() as seeder:
            for config in domain_configs:
                domain = config["domain"]
                pattern = config["pattern"]
                max_urls = config.get("max_urls", 25)

                print(f"\n📍 Domain: {domain}")
                print(f"   Pattern: {pattern}")
                print(f"   Max URLs: {max_urls}")

                try:
                    # Type-specific queries for relevance scoring
                    queries = {
                        "recipe": "recipe ingredients instructions cooking steps directions",
                        "product": "product price buy purchase specifications details",
                        "event": "event date time location venue organizer attend",
                        "pricing_table": "pricing plans features price subscription tier",
                        "job_posting": "job position title company location department career",
                        "person": "person profile bio contact team member faculty",
                    }
                    query = queries.get(fragment_type, "")

                    # Configure sitemap+cc URL discovery (combines sitemap + Common Crawl)
                    # TODO: higher max_urls/concurrency
                    seeding_config = SeedingConfig(
                        source="sitemap+cc",  # Use both sitemap and Common Crawl
                        pattern=pattern,
                        extract_head=True,  # Get metadata for scoring
                        query=query,
                        scoring_method="bm25",
                        score_threshold=0.1,  # Very low threshold for maximum discovery
                        max_urls=max_urls,
                        live_check=False,  # Skip live check for speed
                        concurrency=5,
                    )

                    # Discover URLs
                    urls = await seeder.urls(domain, seeding_config)

                    # Extract just the URL strings (handle dict or object format)
                    url_strings = []
                    for url_item in urls:
                        if isinstance(url_item, dict):
                            url_strings.append(url_item.get("url", str(url_item)))
                        elif hasattr(url_item, "url"):
                            url_strings.append(url_item.url)
                        else:
                            url_strings.append(str(url_item))

                    discovered_urls[domain] = url_strings

                    print(f"   ✓ Discovered {len(url_strings)} URLs")
                    if url_strings:
                        print(f"   Example: {url_strings[0]}")

                except Exception as e:
                    print(f"   ✗ Failed to discover URLs: {e}")
                    discovered_urls[domain] = []

        total_discovered = sum(len(urls) for urls in discovered_urls.values())
        print(f"\n✅ Total discovered: {total_discovered} URLs across {len(discovered_urls)} domains")

        return discovered_urls

    def validate_fragment(self, fragment_html: str, fragment_type: str) -> dict:
        """
        Validate fragment by:
        1. First checking for negative patterns (error pages, auth walls, empty SPAs)
        2. Then counting percentage of positive schema pattern matches

        Returns dict with:
        - is_valid: bool (True if score >= 0.3 and no negative patterns)
        - score: float (0-1) - percentage of validation patterns that matched
        - matched_patterns: list of patterns that matched
        - total_patterns: int - total patterns checked
        - reason: str explanation
        - negative_type: str | None - type of negative if detected (error_page, auth_required, empty_shell)
        """
        soup = BeautifulSoup(fragment_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        # STEP 1: Check for negative patterns first
        # Order matters: check more common patterns first to avoid false positives
        negative_schemas = {
            "auth_required": get_schema("auth_required"),  # Most common: check first
            "empty_shell": get_schema("empty_shell"),
            "error_page": get_schema("error_page"),  # Check last (least common)
        }

        for negative_type, negative_schema in negative_schemas.items():
            if not hasattr(negative_schema, "NEGATIVE_VALIDATION_PATTERNS"):
                continue

            negative_patterns = negative_schema.NEGATIVE_VALIDATION_PATTERNS
            matched_negative = []

            # Check if negative patterns match
            for pattern in negative_patterns:
                try:
                    # Search in both HTML and text
                    if re.search(pattern, fragment_html, re.IGNORECASE) or re.search(pattern, text, re.IGNORECASE):
                        matched_negative.append(pattern)
                except re.error:
                    continue

            # If 3+ negative patterns match, classify as that negative type
            # Higher threshold (3+) prevents false positives from incidental matches
            if len(matched_negative) >= 3:
                return {
                    "is_valid": False,
                    "score": 0.0,
                    "matched_patterns": matched_negative[:5],
                    "total_patterns": len(negative_patterns),
                    "reason": f"Detected {negative_type}: {len(matched_negative)}/{len(negative_patterns)} negative patterns matched",  # noqa: E501
                    "negative_type": negative_type,
                }

        # STEP 2: Check for positive patterns (existing logic)
        try:
            schema = get_schema(fragment_type)
        except ValueError:
            return {
                "is_valid": True,
                "score": 0.5,
                "matched_patterns": [],
                "total_patterns": 0,
                "reason": f"Unknown fragment type: {fragment_type}",
                "negative_type": None,
            }

        if not hasattr(schema, "VALIDATION_PATTERNS"):
            return {
                "is_valid": True,
                "score": 0.5,
                "matched_patterns": [],
                "total_patterns": 0,
                "reason": "No validation patterns defined",
                "negative_type": None,
            }

        patterns = schema.VALIDATION_PATTERNS
        matched_patterns = []

        # Count how many patterns match
        for pattern in patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    matched_patterns.append(pattern)
            except re.error:
                # Skip invalid patterns
                continue

        # Calculate quality score as percentage of patterns matched
        total_patterns = len(patterns)
        score = len(matched_patterns) / total_patterns if total_patterns > 0 else 0.0

        # Simple threshold: valid if at least 30% of patterns match
        is_valid = score >= 0.3

        reason = (
            f"Matched {len(matched_patterns)}/{total_patterns} patterns ({score:.1%})"
            if is_valid
            else f"Only {len(matched_patterns)}/{total_patterns} patterns matched ({score:.1%}) - need 30%+"
        )

        return {
            "is_valid": is_valid,
            "score": score,
            "matched_patterns": matched_patterns[:5],  # Show first 5 for debugging
            "total_patterns": total_patterns,
            "reason": reason,
            "negative_type": None,
        }

    async def fetch_page(self, url: str) -> str | None:
        """Fetch HTML from URL using Crawl4AI."""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(url=url)
                if result.success:
                    return result.html
                print(f"Failed to fetch {url}: {result.error_message}")
                return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_fragment(self, html: str, fragment_type: str) -> str | None:
        """Extract relevant fragment from page HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, and other noise we don't want
        for tag in soup(["script", "style", "noscript", "meta", "link"]):
            tag.decompose()

        if fragment_type == "product":
            # Try to find product container
            candidates = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_=lambda x: x and "product" in x.lower())
            )
            if candidates:
                return str(candidates)

        elif fragment_type == "recipe":
            # Try to find recipe content
            candidates = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=lambda x: x and "recipe" in x.lower())
            )
            if candidates:
                return str(candidates)

        elif fragment_type == "event":
            # Try to find event container
            candidates = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=lambda x: x and "event" in x.lower())
                or soup.find("section", class_=lambda x: x and "event" in x.lower())
            )
            if candidates:
                return str(candidates)

        elif fragment_type == "pricing_table":
            # Try to find pricing container
            candidates = (
                soup.find("section", class_=lambda x: x and "pricing" in x.lower())
                or soup.find("div", class_=lambda x: x and "pricing" in x.lower())
                or soup.find("main")
            )
            if candidates:
                return str(candidates)

        elif fragment_type == "job_posting":
            # Try to find job posting container
            candidates = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=lambda x: x and ("job" in x.lower() or "posting" in x.lower()))
            )
            if candidates:
                return str(candidates)

        elif fragment_type == "person":
            # Try to find person profile container
            candidates = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=lambda x: x and ("profile" in x.lower() or "person" in x.lower()))
                or soup.find("section", class_=lambda x: x and "bio" in x.lower())
            )
            if candidates:
                return str(candidates)

        # Fallback: return body
        body = soup.find("body")
        return str(body) if body else html

    def save_fragment(self, fragment_html: str, fragment_type: str, source_url: str, validation_result: dict):
        """Save fragment as candidate."""
        fragment_id = self._get_fragment_id(fragment_html)

        # Save HTML
        html_path = self.candidates_dir / f"{fragment_type}_{fragment_id}.html"
        html_path.write_text(fragment_html)

        # Save metadata with validation results
        metadata = {
            "fragment_id": fragment_id,
            "fragment_type": fragment_type,
            "source_url": source_url,
            "confidence": "high",  # Curated sources = high confidence
            "status": "candidate",
            "requires_annotation": True,
            "validation": {
                "score": validation_result["score"],
                "matched_patterns": validation_result.get("matched_patterns", []),
                "total_patterns": validation_result.get("total_patterns", 0),
            },
        }
        metadata_path = self.candidates_dir / f"{fragment_type}_{fragment_id}.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # Create annotation template
        self._create_annotation_template(fragment_type, fragment_id)

        print(f"✓ Saved {fragment_type} fragment: {fragment_id} (score: {validation_result['score']:.2%})")
        print(f"  Source: {source_url}")
        print(
            f"  Matched: {len(validation_result.get('matched_patterns', []))}/{validation_result.get('total_patterns', 0)} patterns"  # noqa: E501
        )
        print(f"  Files: {html_path.name}, {metadata_path.name}")

    def save_negative_fragment(self, fragment_html: str, fragment_type: str, source_url: str, validation_result: dict):
        """Save rejected fragment as negative example with descriptive naming."""
        fragment_id = self._get_fragment_id(fragment_html)

        # Determine prefix based on negative_type classification
        negative_type = validation_result.get("negative_type")
        if negative_type == "error_page":
            prefix = "errorpage"
        elif negative_type == "auth_required":
            prefix = "authrequired"
        elif negative_type == "empty_shell":
            prefix = "emptyspashell"
        else:
            # Generic negative (low score, no specific anti-pattern detected)
            prefix = f"{fragment_type}_lowscore"

        # Save HTML with descriptive name
        html_path = self.negatives_dir / f"{prefix}_{fragment_id}.html"
        html_path.write_text(fragment_html)

        # Save metadata with rejection reason
        metadata = {
            "fragment_id": fragment_id,
            "expected_type": fragment_type,  # What it was supposed to be
            "negative_type": negative_type,  # Specific negative classification (or None)
            "source_url": source_url,
            "status": "negative",
            "rejection_reason": validation_result["reason"],
            "validation": {
                "score": validation_result["score"],
                "matched_patterns": validation_result.get("matched_patterns", []),
                "total_patterns": validation_result.get("total_patterns", 0),
            },
            "requires_annotation": True,
        }
        metadata_path = self.negatives_dir / f"{prefix}_{fragment_id}.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # Create negative annotation template
        self._create_negative_annotation_template(prefix, fragment_id, validation_result)

        # Enhanced output
        negative_label = negative_type if negative_type else "low score"
        print(f"✓ Saved negative fragment [{negative_label}]: {fragment_id}")
        print(f"  Type: {prefix}")
        print(f"  Expected: {fragment_type}")
        print(f"  Score: {validation_result['score']:.2%}")
        print(f"  Rejection: {validation_result['reason']}")
        print(f"  Files: {html_path.name}, {metadata_path.name}")

    def _create_negative_annotation_template(self, prefix: str, fragment_id: str, validation_result: dict):
        """Create annotation template for negative examples."""
        template_path = self.negatives_dir / f"{prefix}_{fragment_id}_annotation.json"

        negative_type = validation_result.get("negative_type")

        # Create type-specific templates
        if negative_type == "error_page":
            template = {
                "type": "error_page",
                "error_code": "TODO: Extract error code (e.g., 404, 500)",
                "message": "TODO: Extract error message",
                "description": "TODO: Extract error description",
                "matched_negative_patterns": validation_result.get("matched_patterns", []),
            }
        elif negative_type == "auth_required":
            template = {
                "type": "auth_required",
                "message": "TODO: Extract auth required message",
                "description": "TODO: Extract description (e.g., 'Please log in to view this content')",
                "content_available": False,
                "matched_negative_patterns": validation_result.get("matched_patterns", []),
            }
        elif negative_type == "empty_shell":
            template = {
                "type": "empty_shell",
                "framework": "TODO: Identify framework (react, vue, angular) or null",
                "content_available": False,
                "reason": "client_side_rendering",
                "matched_negative_patterns": validation_result.get("matched_patterns", []),
            }
        else:
            # Generic low-score negative
            template = {
                "type": "negative",
                "expected_type": prefix.replace("_lowscore", ""),
                "rejection_reason": validation_result["reason"],
                "matched_patterns": validation_result.get("matched_patterns", []),
                "total_patterns": validation_result.get("total_patterns", 0),
                "negative_indicator_fragment": (
                    "TODO: Extract the HTML fragment that shows why this is negative "
                    f"(only {validation_result.get('score', 0):.1%} of patterns matched)"
                ),
                "notes": "TODO: Any additional notes about why this failed validation",
            }

        template_path.write_text(json.dumps(template, indent=2))
        print(f"  Negative annotation template: {template_path.name}")

    def _create_annotation_template(self, fragment_type: str, fragment_id: str):
        """Create JSON annotation template."""
        template_path = self.candidates_dir / f"{fragment_type}_{fragment_id}_annotation.json"

        if fragment_type == "product":
            template = {
                "type": "product",
                "name": "TODO: Extract product name",
                "brand": "TODO: Extract brand (or null)",
                "price": {"current": 0.0, "original": None, "currency": "USD"},
                "rating": {"score": 0.0, "review_count": 0},
                "description": "TODO: Extract description",
                "availability": "in_stock",
                "image_url": "TODO: Extract image URL (or null)",
            }
        elif fragment_type == "recipe":
            template = {
                "type": "recipe",
                "name": "TODO: Extract recipe name",
                "description": "TODO: Extract description (or null)",
                "author": "TODO: Extract author (or null)",
                "prep_time": "TODO: e.g., '15 min'",
                "cook_time": "TODO: e.g., '30 min' (or null)",
                "total_time": "TODO: e.g., '45 min' (or null)",
                "servings": "TODO: e.g., '4 servings'",
                "ingredients": ["TODO: Ingredient 1", "TODO: Ingredient 2"],
                "instructions": ["TODO: Step 1", "TODO: Step 2"],
                "rating": None,
            }
        elif fragment_type == "event":
            template = {
                "type": "event",
                "title": "TODO: Extract event title",
                "datetime": "TODO: e.g., 'Tue, Dec 16 · 6:00 PM SST'",
                "location": "TODO: Extract location (or 'Online')",
                "venue_name": "TODO: Extract venue name (or null)",
                "price": "TODO: e.g., 'Free', '$25', or null",
                "organizer": "TODO: Extract organizer (or null)",
                "attendee_count": None,
                "description": "TODO: Extract description (or null)",
                "event_type": "TODO: 'online' or 'in_person' (or null)",
            }
        elif fragment_type == "pricing_table":
            template = {
                "type": "pricing_table",
                "plans": [
                    {
                        "name": "TODO: Plan 1 name (e.g., 'Basic')",
                        "price": "TODO: e.g., 'Free', '$10/month'",
                        "price_amount": None,
                        "currency": "USD",
                        "billing_period": "TODO: 'month', 'year', or 'one_time'",
                        "features": ["TODO: Feature 1", "TODO: Feature 2"],
                        "description": "TODO: Plan description (or null)",
                    },
                    {
                        "name": "TODO: Plan 2 name (e.g., 'Pro')",
                        "price": "TODO: e.g., '$29/month'",
                        "price_amount": 29.0,
                        "currency": "USD",
                        "billing_period": "month",
                        "features": ["TODO: Feature 1", "TODO: Feature 2"],
                        "description": "TODO: Plan description (or null)",
                    },
                ],
            }
        elif fragment_type == "job_posting":
            template = {
                "type": "job_posting",
                "title": "TODO: Extract job title",
                "company": "TODO: Extract company name",
                "location": "TODO: e.g., 'Remote', 'San Francisco, CA'",
                "department": "TODO: Extract department (or null)",
                "posted_date": "TODO: e.g., '4 days ago', '2025-12-15'",
                "employment_type": "TODO: e.g., 'Full-time' (or null)",
                "description": "TODO: Extract job description snippet (or null)",
            }
        elif fragment_type == "person":
            template = {
                "type": "person",
                "name": "TODO: Extract person name",
                "title": "TODO: Extract title/role (or null)",
                "bio": "TODO: Extract bio (or null)",
                "email": "TODO: Extract email (or null)",
                "phone": "TODO: Extract phone (or null)",
                "linkedin": "TODO: Extract LinkedIn URL (or null)",
                "image_url": "TODO: Extract profile image URL (or null)",
            }
        else:
            template = {"type": fragment_type, "TODO": "Define schema"}

        template_path.write_text(json.dumps(template, indent=2))
        print(f"  Annotation template: {template_path.name}")

    async def collect_with_deep_crawl(self, fragment_type: str, config: dict):
        """
        Collect fragments using deep crawling from a seed URL.

        Args:
            fragment_type: Type of fragment (e.g., 'auth_required')
            config: Dict with 'seed_url' and 'max_pages'
        """
        seed_url = config["seed_url"]
        max_pages = config.get("max_pages", 10)

        print(f"\n🔍 Deep crawling: {seed_url}")
        print(f"   Max pages: {max_pages}")

        # Configure URL filters for authrequired
        if fragment_type == "authrequired":
            # Match login/signin/auth URLs
            filter_chain = FilterChain(
                [
                    URLPatternFilter(
                        patterns=[
                            "*/login*",
                            "*/signin*",
                            "*/sign-in*",
                            "*/auth*",
                            "*/accounts/*",
                            "*/user/login*",
                        ]
                    )
                ]
            )
        elif fragment_type == "paywall_content":
            # Match article URLs
            filter_chain = FilterChain(
                [
                    URLPatternFilter(
                        patterns=[
                            "*/article/*",
                            "*/articles/*",
                            "*/story/*",
                            "*/p/*",  # Medium
                        ]
                    )
                ]
            )
        else:
            filter_chain = None

        # Configure deep crawling strategy
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=max_pages,
            include_external=False,
            filter_chain=filter_chain,
        )

        crawl_config = CrawlerRunConfig(
            deep_crawl_strategy=deep_crawl_strategy,
        )

        collected = 0
        rejected = 0

        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                # Deep crawl returns a list of results
                results = await crawler.arun(url=seed_url, config=crawl_config)

                # Handle both list and single result container
                if not isinstance(results, list):
                    results = [results]

                # Iterate through all crawled results
                for result in results:
                    if not result.success:
                        continue

                    # Extract fragment
                    fragment_html = self.extract_fragment(result.html, fragment_type)
                    if not fragment_html:
                        continue

                    # Validate
                    validation_result = self.validate_fragment(fragment_html, fragment_type)

                    # Save based on validation
                    if validation_result["is_valid"]:
                        self.save_fragment(fragment_html, fragment_type, result.url, validation_result)
                        collected += 1
                    else:
                        self.save_negative_fragment(fragment_html, fragment_type, result.url, validation_result)
                        rejected += 1

        except Exception as e:
            print(f"   ❌ Error during deep crawl: {e}")

        print(f"   ✓ Collected: {collected} positive, {rejected} negative")
        return collected, rejected

    async def collect_fragments(self, categories: list[str] | None = None):
        """Collect fragments using sitemap-based URL discovery.

        Args:
            categories: List of categories to collect (e.g., ['recipe', 'product']).
                       If None, collects all categories.
        """
        # Filter categories
        if categories:
            fragment_types = [t for t in categories if t in self.domain_configs]
            if not fragment_types:
                print(f"❌ No valid categories specified. Available: {list(self.domain_configs.keys())}")
                return
        else:
            fragment_types = list(self.domain_configs.keys())

        print("\n" + "=" * 70)
        print("🚀 COLLECTING FRAGMENTS USING CRAWL4AI URL SEEDING")
        print(f"📦 Categories: {', '.join(fragment_types)}")
        print("=" * 70)

        total_collected = 0
        total_rejected = 0
        total_discovered = 0
        validation_stats = {"valid": 0, "invalid": 0, "total_score": 0.0}

        for fragment_type in fragment_types:
            print(f"\n📦 Processing {fragment_type.upper()} fragments...")
            print("=" * 70)

            # Check if this type uses deep crawling
            domain_configs = self.domain_configs.get(fragment_type, [])
            uses_deep_crawl = domain_configs and "seed_url" in domain_configs[0]

            if uses_deep_crawl:
                # Use deep crawling for negative types (auth_required, paywall_content)
                print(f"🔍 Using deep crawling from {len(domain_configs)} seed URLs...")
                print("-" * 70)

                for config in domain_configs:
                    collected, rejected = await self.collect_with_deep_crawl(fragment_type, config)
                    total_collected += collected
                    total_rejected += rejected

                continue

            # Step 1: Discover URLs from sitemaps (traditional approach)
            discovered_urls = await self.discover_urls(fragment_type)
            domain_url_count = sum(len(urls) for urls in discovered_urls.values())
            total_discovered += domain_url_count

            # Step 2: Fetch and process each discovered URL
            print(f"\n📥 Fetching and validating {domain_url_count} discovered URLs...")
            print("-" * 70)

            for domain, urls in discovered_urls.items():
                print(f"\n🌐 Processing {len(urls)} URLs from {domain}")

                for url in urls:
                    print(f"\n  Fetching: {url}")

                    # Fetch page
                    html = await self.fetch_page(url)
                    if not html:
                        print("    ✗ Failed to fetch page")
                        continue

                    print(f"    ✓ Fetched HTML ({len(html)} bytes)")

                    # Extract fragment
                    fragment_html = self.extract_fragment(html, fragment_type)
                    if not fragment_html:
                        print("    ✗ Failed to extract fragment")
                        continue

                    print(f"    ✓ Extracted fragment ({len(fragment_html)} bytes)")

                    # Validate fragment
                    validation_result = self.validate_fragment(fragment_html, fragment_type)
                    print(f"    📊 Validation: {validation_result['reason']}")
                    print(f"       Score: {validation_result['score']:.2f}")

                    if not validation_result["is_valid"]:
                        print(f"    ✗ Fragment rejected - {validation_result['reason']}")
                        # Save as negative example
                        self.save_negative_fragment(fragment_html, fragment_type, url, validation_result)
                        total_rejected += 1
                        validation_stats["invalid"] += 1
                        continue

                    # Save fragment with validation results
                    self.save_fragment(fragment_html, fragment_type, url, validation_result)
                    total_collected += 1
                    validation_stats["valid"] += 1
                    validation_stats["total_score"] += validation_result["score"]

        print("\n" + "=" * 70)
        print("✅ Collection complete!")
        print("=" * 70)
        print(f"Discovered: {total_discovered} URLs")
        print(f"Collected (positive): {total_collected} fragments")
        print(f"Collected (negative): {total_rejected} fragments")
        if total_collected > 0:
            avg_score = validation_stats["total_score"] / total_collected
            print(f"Average quality score: {avg_score:.2f}")
        if total_discovered > 0:
            success_rate = (total_collected / total_discovered) * 100
            print(f"Success rate: {success_rate:.1f}%")
            rejection_rate = (total_rejected / total_discovered) * 100
            print(f"Rejection rate: {rejection_rate:.1f}%")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Review positive fragments in data/seeds/candidates/")
        print("2. Review negative fragments in data/seeds/negatives/")
        print("3. Fill in annotation templates (*_annotation.json)")
        print("4. Use streamlit app: streamlit run scripts/label_app.py")
        print("\nNote: E-commerce and job posting sites typically have high rejection")
        print("rates due to SPAs, login walls, and missing fields - these make")
        print("excellent negative examples for training!")
        print("=" * 70 + "\n")

    def reclassify_negatives(self, auto_rename: bool = True):
        """
        Re-classify existing negative fragments using new negative pattern detection.

        Analyzes existing negatives and classifies them into specific negative types
        (error_page, auth_required, empty_shell). Deletes fragments that are only
        low_score (no specific negative type detected).

        Args:
            auto_rename: If True, automatically rename files to match new classification
        """
        negative_files = sorted(self.negatives_dir.glob("*.html"))

        if not negative_files:
            print(f"\n⚠️  No negative HTML files found in {self.negatives_dir}")
            return

        print("\n" + "=" * 70)
        print(f"🔍 RE-CLASSIFYING {len(negative_files)} NEGATIVE FRAGMENTS")
        print("=" * 70 + "\n")

        # Track statistics
        negative_type_counts = Counter()
        results = []
        renamed_count = 0
        deleted_count = 0

        for i, html_file in enumerate(negative_files):
            # Parse expected type from filename
            parts = html_file.stem.split("_")
            if parts[0] == "job" and len(parts) > 1 and parts[1] == "posting":
                expected_type = "job_posting"
            else:
                # Try to infer from filename or default to product
                expected_type = (
                    parts[0] if parts[0] in ["recipe", "product", "event", "pricing", "person"] else "product"
                )

            # Extract fragment_id (last part of filename)
            fragment_id = parts[-1]

            # Read HTML
            with open(html_file, encoding="utf-8", errors="replace") as f:
                html = f.read()

            # Validate using new system
            validation_result = self.validate_fragment(html, expected_type)

            negative_type = validation_result.get("negative_type")
            negative_type_counts[negative_type or "low_score"] += 1

            # Determine new prefix
            if negative_type == "error_page":
                new_prefix = "errorpage"
            elif negative_type == "auth_required":
                new_prefix = "authrequired"
            elif negative_type == "empty_shell":
                new_prefix = "emptyspashell"
            else:
                # No specific negative type - mark for deletion
                new_prefix = None

            old_name = html_file.name

            # Delete low_score fragments (no specific negative type)
            if new_prefix is None:
                # Delete HTML file
                html_file.unlink()

                # Delete JSON metadata if exists
                old_json = html_file.with_suffix(".json")
                if old_json.exists():
                    old_json.unlink()

                # Delete annotation template if exists
                old_annotation = self.negatives_dir / f"{html_file.stem}_annotation.json"
                if old_annotation.exists():
                    old_annotation.unlink()

                deleted_count += 1

                results.append(
                    {
                        "old_file": old_name,
                        "deleted": True,
                        "expected_type": expected_type,
                        "negative_type": "low_score",
                        "score": validation_result["score"],
                        "reason": validation_result["reason"],
                        "matched_patterns": len(validation_result.get("matched_patterns", [])),
                    }
                )
            else:
                # Rename to specific negative type
                new_name = f"{new_prefix}_{fragment_id}.html"
                needs_rename = old_name != new_name

                if auto_rename and needs_rename:
                    # Rename HTML file
                    new_html_path = self.negatives_dir / new_name
                    html_file.rename(new_html_path)

                    # Rename JSON metadata if exists
                    old_json = html_file.with_suffix(".json")
                    if old_json.exists():
                        new_json = self.negatives_dir / f"{new_prefix}_{fragment_id}.json"
                        old_json.rename(new_json)

                        # Update metadata with new negative_type
                        with open(new_json) as f:
                            metadata = json.load(f)
                        metadata["negative_type"] = negative_type
                        metadata["rejection_reason"] = validation_result["reason"]
                        with open(new_json, "w") as f:
                            json.dump(metadata, f, indent=2)

                    # Rename annotation template if exists
                    old_annotation = self.negatives_dir / f"{html_file.stem}_annotation.json"
                    if old_annotation.exists():
                        new_annotation = self.negatives_dir / f"{new_prefix}_{fragment_id}_annotation.json"
                        old_annotation.rename(new_annotation)

                    renamed_count += 1

                results.append(
                    {
                        "old_file": old_name,
                        "new_file": new_name if needs_rename else old_name,
                        "renamed": needs_rename and auto_rename,
                        "deleted": False,
                        "expected_type": expected_type,
                        "negative_type": negative_type,
                        "new_prefix": new_prefix,
                        "score": validation_result["score"],
                        "reason": validation_result["reason"],
                        "matched_patterns": len(validation_result.get("matched_patterns", [])),
                    }
                )

            # Print status every 10 files
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(negative_files)} files...")

        # Print results summary
        print(f"\n{'=' * 70}")
        print("CLASSIFICATION RESULTS")
        print(f"{'=' * 70}\n")

        print("Negative Type Distribution:")
        for neg_type, count in negative_type_counts.most_common():
            pct = count / len(negative_files) * 100
            status = "(deleted)" if neg_type == "low_score" else ""
            print(f"  {neg_type:20s}: {count:3d} ({pct:5.1f}%) {status}")

        print(f"\n🗑️  Deleted {deleted_count}/{len(negative_files)} low_score files")
        if auto_rename:
            print(f"📝 Renamed {renamed_count}/{len(negative_files)} files to specific negative types")

        # Print examples of each type (excluding deleted low_score)
        print(f"\n{'=' * 70}")
        print("EXAMPLES BY NEGATIVE TYPE (kept files only)")
        print(f"{'=' * 70}\n")

        for neg_type in ["error_page", "auth_required", "empty_shell"]:
            examples = [r for r in results if r["negative_type"] == neg_type and not r.get("deleted", False)]
            if examples:
                print(f"\n{neg_type.upper()} ({len(examples)} examples):")
                for example in examples[:3]:  # Show first 3
                    print(f"  • {example['old_file']}")
                    if example.get("renamed", False):
                        print(f"    → Renamed to: {example['new_file']}")
                    print(f"    Expected: {example['expected_type']}")
                    print(f"    New prefix: {example['new_prefix']}")
                    print(f"    Score: {example['score']:.2%}")
                    print(f"    Reason: {example['reason']}")
                    print(f"    Matched patterns: {example['matched_patterns']}")
                    print()

        # Save detailed results to JSON
        output_file = self.negatives_dir.parent / "negative_reclassification_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n{'=' * 70}")
        print("✅ Re-classification complete!")
        print(f"Detailed results saved to: {output_file}")
        print(f"{'=' * 70}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect HTML fragments using Crawl4AI URL seeding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect all categories
  python scripts/00_collect.py

  # Collect only recipes
  python scripts/00_collect.py --categories recipe

  # Collect only products
  python scripts/00_collect.py --categories product

  # Collect events and pricing tables
  python scripts/00_collect.py --categories event pricing_table

  # Run in parallel (separate terminals)
  python scripts/00_collect.py --categories recipe &
  python scripts/00_collect.py --categories product &
  python scripts/00_collect.py --categories event &
  python scripts/00_collect.py --categories pricing_table &
        """,
    )
    parser.add_argument(
        "--categories",
        "-c",
        nargs="+",
        choices=[
            "recipe",
            "product",
            "event",
            "pricing_table",
            "job_posting",
            "person",
            "paywall_content",
            "spa_heavy",
            "authrequired",
            "error_page",
        ],
        help="Categories to collect (default: all). Includes negative collectors: paywall_content, spa_heavy, authrequired, error_page",  # noqa: E501
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    collector = FragmentCollector(project_root)

    await collector.collect_fragments(categories=args.categories)


if __name__ == "__main__":
    asyncio.run(main())
