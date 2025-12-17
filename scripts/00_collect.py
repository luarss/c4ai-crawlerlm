import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path
from typing import ClassVar

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

from src.schemas import generate_annotation_template, get_schema


class FragmentCollector:
    """Collect fragment candidates from domains using Crawl4AI URL seeding."""

    # =========================================================================
    # INITIALIZATION & CONFIGURATION
    # =========================================================================

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
                # Company career pages
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
                # University faculty/staff pages
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
                {
                    "domain": "harvard.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                {
                    "domain": "cornell.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                {
                    "domain": "cmu.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                {
                    "domain": "princeton.edu",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                # Research institutions
                {
                    "domain": "nist.gov",
                    "pattern": "*/staff/*",
                    "max_urls": 15,
                },
                {
                    "domain": "nasa.gov",
                    "pattern": "*/people/*",
                    "max_urls": 15,
                },
                # Company team pages
                {
                    "domain": "stripe.com",
                    "pattern": "*/about/team*",
                    "max_urls": 15,
                },
                {
                    "domain": "anthropic.com",
                    "pattern": "*/team*",
                    "max_urls": 15,
                },
                {
                    "domain": "openai.com",
                    "pattern": "*/team*",
                    "max_urls": 15,
                },
                {
                    "domain": "deepmind.com",
                    "pattern": "*/team/*",
                    "max_urls": 15,
                },
                # Speaker/author bios
                {
                    "domain": "tedxtalks.ted.com",
                    "pattern": "*/speakers/*",
                    "max_urls": 20,
                },
                {
                    "domain": "oreilly.com",
                    "pattern": "*/people/*",
                    "max_urls": 20,
                },
                # Professional profiles
                {
                    "domain": "acm.org",
                    "pattern": "*/people/*",
                    "max_urls": 15,
                },
                {
                    "domain": "ieee.org",
                    "pattern": "*/people/*",
                    "max_urls": 15,
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
            "empty_spa_shell": [
                # Intentionally collect empty SPA shells with minimal server-rendered content
                # These serve as negative examples where content requires JavaScript to render
                # React SPAs
                {
                    "seed_url": "https://www.netflix.com",
                    "max_pages": 10,
                    "url_patterns": ["*/browse*", "*/title/*"],
                },
                {
                    "seed_url": "https://www.instagram.com",
                    "max_pages": 10,
                    "url_patterns": ["*/explore/*", "*/p/*"],
                },
                {
                    "seed_url": "https://www.reddit.com",
                    "max_pages": 10,
                    "url_patterns": ["*/r/*"],
                },
                {
                    "seed_url": "https://app.slack.com",
                    "max_pages": 10,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.notion.so",
                    "max_pages": 10,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://trello.com",
                    "max_pages": 10,
                    "url_patterns": None,
                },
                # Vue/Nuxt SPAs
                {
                    "seed_url": "https://nuxt.com",
                    "max_pages": 10,
                    "url_patterns": ["*/docs/*"],
                },
                # Angular SPAs
                {
                    "seed_url": "https://angular.io",
                    "max_pages": 10,
                    "url_patterns": ["*/docs/*", "*/start*"],
                },
                {
                    "seed_url": "https://material.angular.io",
                    "max_pages": 10,
                    "url_patterns": ["*/components/*"],
                },
                # Web apps with heavy client-side rendering
                {
                    "seed_url": "https://www.figma.com",
                    "max_pages": 10,
                    "url_patterns": ["*/files/*", "*/file/*"],
                },
                {
                    "seed_url": "https://www.canva.com",
                    "max_pages": 10,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.spotify.com",
                    "max_pages": 10,
                    "url_patterns": ["*/playlist/*", "*/album/*", "*/artist/*"],
                },
                {
                    "seed_url": "https://app.asana.com",
                    "max_pages": 10,
                    "url_patterns": None,
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
            "errorpage": [
                # Crawl sites to find naturally occurring error pages
                # This captures real 404s, 410s, deleted content, moved pages, etc.
                {
                    "seed_url": "https://github.com",
                    "max_pages": 20,
                    "url_patterns": None,  # Crawl all pages to find broken links
                },
                {
                    "seed_url": "https://stackoverflow.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.reddit.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://medium.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://twitter.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.youtube.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.amazon.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://stripe.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.linkedin.com",
                    "max_pages": 20,
                    "url_patterns": None,
                },
            ],
            "captcha_or_bot_check": [
                # Intentionally trigger rate limits/bot checks by rapid requests
                # These sites commonly use Cloudflare, DataDome, or similar protection
                {
                    "seed_url": "https://www.ticketmaster.com",
                    "max_pages": 15,
                    "url_patterns": None,  # No filter - explore all pages to trigger captcha
                },
                {
                    "seed_url": "https://www.stubhub.com",
                    "max_pages": 15,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.seatgeek.com",
                    "max_pages": 15,
                    "url_patterns": None,
                },
                {
                    "seed_url": "https://www.zillow.com",
                    "max_pages": 15,
                    "url_patterns": ["*/homedetails/*", "*/b/*"],  # Browse listings to trigger limits
                },
                {
                    "seed_url": "https://www.redfin.com",
                    "max_pages": 15,
                    "url_patterns": ["*/home/*", "*/city/*"],  # Browse properties
                },
                {
                    "seed_url": "https://www.bestbuy.com",
                    "max_pages": 15,
                    "url_patterns": ["*/site/*", "*/products/*"],  # Browse products
                },
                {
                    "seed_url": "https://www.target.com",
                    "max_pages": 15,
                    "url_patterns": ["*/p/*", "*/c/*"],  # Browse products
                },
            ],
        }

    # Fragment extraction selectors configuration
    FRAGMENT_SELECTORS: ClassVar[dict[str, list[tuple]]] = {
        "recipe": [
            ("article", {}),
            ("main", {}),
            ("div", {"class_": lambda x: x and "recipe" in x.lower()}),
        ],
        "event": [
            ("article", {}),
            ("main", {}),
            ("div", {"class_": lambda x: x and "event" in x.lower()}),
            ("section", {"class_": lambda x: x and "event" in x.lower()}),
        ],
        "pricing_table": [
            ("section", {"class_": lambda x: x and "pricing" in x.lower()}),
            ("div", {"class_": lambda x: x and "pricing" in x.lower()}),
            ("main", {}),
        ],
        "job_posting": [
            ("article", {}),
            ("main", {}),
            ("div", {"class_": lambda x: x and ("job" in x.lower() or "posting" in x.lower())}),
        ],
        "person": [
            ("article", {}),
            ("main", {}),
            ("div", {"class_": lambda x: x and ("profile" in x.lower() or "person" in x.lower())}),
            ("section", {"class_": lambda x: x and "bio" in x.lower()}),
        ],
    }

    # =========================================================================
    # URL DISCOVERY METHODS
    # =========================================================================

    def _get_discovery_query(self, fragment_type: str) -> str:
        """Get type-specific query for relevance scoring."""
        queries = {
            "recipe": "recipe ingredients instructions cooking steps directions",
            "event": "event date time location venue organizer attend",
            "pricing_table": "pricing plans features price subscription tier",
            "job_posting": "job position title company location department career",
            "person": "person profile bio contact team member faculty",
        }
        return queries.get(fragment_type, "")

    def _extract_url_strings(self, urls: list) -> list[str]:
        """Extract URL strings from various formats."""
        url_strings = []
        for url_item in urls:
            if isinstance(url_item, dict):
                url_strings.append(url_item.get("url", str(url_item)))
            elif hasattr(url_item, "url"):
                url_strings.append(url_item.url)
            else:
                url_strings.append(str(url_item))
        return url_strings

    async def _discover_domain_urls(
        self, seeder, domain: str, pattern: str, max_urls: int, fragment_type: str
    ) -> list[str]:
        """Discover URLs for a single domain."""
        print(f"\n📍 Domain: {domain}")
        print(f"   Pattern: {pattern}")
        print(f"   Max URLs: {max_urls}")

        try:
            query = self._get_discovery_query(fragment_type)

            # Configure sitemap+cc URL discovery (combines sitemap + Common Crawl)
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
            url_strings = self._extract_url_strings(urls)

            print(f"   ✓ Discovered {len(url_strings)} URLs")
            if url_strings:
                print(f"   Example: {url_strings[0]}")

            return url_strings

        except Exception as e:
            print(f"   ✗ Failed to discover URLs: {e}")
            return []

    async def discover_urls(self, fragment_type: str) -> dict[str, list[str]]:
        """Discover URLs from domain sitemaps using AsyncUrlSeeder."""
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

                url_strings = await self._discover_domain_urls(seeder, domain, pattern, max_urls, fragment_type)
                discovered_urls[domain] = url_strings

        total_discovered = sum(len(urls) for urls in discovered_urls.values())
        print(f"\n✅ Total discovered: {total_discovered} URLs across {len(discovered_urls)} domains")

        return discovered_urls

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================

    def _check_negative_patterns(self, fragment_html: str, text: str) -> dict | None:
        """Check for negative patterns."""
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
            matched_negative = self._match_patterns(negative_patterns, fragment_html, text)

            # If 5+ negative patterns match, classify as that negative type
            # Higher threshold (5+) prevents false positives from hidden error banners/templates
            if len(matched_negative) >= 5:
                return {
                    "is_valid": False,
                    "score": 0.0,
                    "matched_patterns": matched_negative[:5],
                    "total_patterns": len(negative_patterns),
                    "reason": f"Detected {negative_type}: {len(matched_negative)}/{len(negative_patterns)} negative patterns matched",  # noqa: E501
                    "negative_type": negative_type,
                }

        return None

    def _match_patterns(self, patterns: list[str], *texts: str) -> list[str]:
        """Match regex patterns against one or more text strings."""
        matched = []
        for pattern in patterns:
            try:
                if any(re.search(pattern, text, re.IGNORECASE) for text in texts):
                    matched.append(pattern)
            except re.error:
                continue
        return matched

    def _check_positive_patterns(self, text: str, fragment_type: str) -> dict:
        """Check for positive patterns."""
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
        matched_patterns = self._match_patterns(patterns, text)

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

    def validate_fragment(self, fragment_html: str, fragment_type: str) -> dict:
        """Validate fragment by checking negative patterns, then positive pattern matches."""
        soup = BeautifulSoup(fragment_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        # STEP 1: Check for negative patterns first
        negative_result = self._check_negative_patterns(fragment_html, text)
        if negative_result:
            return negative_result

        # STEP 2: Check for positive patterns
        return self._check_positive_patterns(text, fragment_type)

    # =========================================================================
    # FRAGMENT EXTRACTION METHODS
    # =========================================================================

    async def fetch_page(self, url: str) -> tuple[str | None, int | None]:
        """Fetch HTML from URL using Crawl4AI."""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(url=url)
                if result.success:
                    status_code = getattr(result, "status_code", None)
                    return result.html, status_code
                print(f"Failed to fetch {url}: {result.error_message}")
                return None, None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None, None

    def extract_fragment(self, html: str, fragment_type: str) -> str | None:
        """Extract relevant fragment from page HTML using configured selectors."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, and other noise we don't want
        for tag in soup(["script", "style", "noscript", "meta", "link"]):
            tag.decompose()

        # Get selectors for this fragment type
        selectors = self.FRAGMENT_SELECTORS.get(fragment_type, [])

        # Try each selector in order until we find a match
        for tag_name, attrs in selectors:
            candidate = soup.find(tag_name, **attrs)
            if candidate:
                return str(candidate)

        # Fallback: return body
        body = soup.find("body")
        return str(body) if body else html

    # =========================================================================
    # STORAGE METHODS
    # =========================================================================

    def _get_fragment_id(self, html: str) -> str:
        """Generate unique ID for fragment."""
        return hashlib.md5(html.encode()).hexdigest()[:8]

    def _save_fragment_files(
        self,
        fragment_html: str,
        filename_prefix: str,
        output_dir: Path,
        metadata: dict,
        create_annotation_fn,
    ) -> tuple[Path, Path, str]:
        """Common helper to save fragment HTML, metadata, and annotation template."""
        fragment_id = self._get_fragment_id(fragment_html)

        # Save HTML
        html_path = output_dir / f"{filename_prefix}_{fragment_id}.html"
        html_path.write_text(fragment_html)

        # Save metadata JSON
        metadata_path = output_dir / f"{filename_prefix}_{fragment_id}.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # Create annotation template
        create_annotation_fn(filename_prefix, fragment_id)

        return html_path, metadata_path, fragment_id

    def save_fragment(self, fragment_html: str, fragment_type: str, source_url: str, validation_result: dict):
        """Save fragment as candidate."""
        # Prepare metadata
        metadata = {
            "fragment_id": self._get_fragment_id(fragment_html),
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

        # Save files using common helper
        html_path, metadata_path, fragment_id = self._save_fragment_files(
            fragment_html,
            fragment_type,
            self.candidates_dir,
            metadata,
            self._create_annotation_template,
        )

        # Print success message
        print(f"✓ Saved {fragment_type} fragment: {fragment_id} (score: {validation_result['score']:.2%})")
        print(f"  Source: {source_url}")
        print(
            f"  Matched: {len(validation_result.get('matched_patterns', []))}/{validation_result.get('total_patterns', 0)} patterns"  # noqa: E501
        )
        print(f"  Files: {html_path.name}, {metadata_path.name}")

    def _get_negative_prefix(self, fragment_type: str, negative_type: str | None) -> str:
        """Determine filename prefix for negative fragment based on classification."""
        if negative_type is None:
            # Generic negative (low score, no specific anti-pattern detected)
            return f"{fragment_type}_lowscore"

        prefix_mapping = {
            "error_page": "errorpage",
            "auth_required": "authrequired",
            "empty_shell": "emptyspashell",
        }
        return prefix_mapping.get(negative_type, f"{fragment_type}_lowscore")

    def save_negative_fragment(self, fragment_html: str, fragment_type: str, source_url: str, validation_result: dict):
        """Save rejected fragment as negative example with descriptive naming."""
        negative_type = validation_result.get("negative_type")
        prefix = self._get_negative_prefix(fragment_type, negative_type)

        # Prepare metadata
        metadata = {
            "fragment_id": self._get_fragment_id(fragment_html),
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

        # Save files using common helper
        html_path, metadata_path, fragment_id = self._save_fragment_files(
            fragment_html,
            prefix,
            self.negatives_dir,
            metadata,
            lambda p, fid: self._create_negative_annotation_template(p, fid, validation_result),
        )

        # Print enhanced output
        negative_label = negative_type if negative_type else "low score"
        print(f"✓ Saved negative fragment [{negative_label}]: {fragment_id}")
        print(f"  Type: {prefix}")
        print(f"  Expected: {fragment_type}")
        print(f"  Score: {validation_result['score']:.2%}")
        print(f"  Rejection: {validation_result['reason']}")
        print(f"  Files: {html_path.name}, {metadata_path.name}")

    # =========================================================================
    # ANNOTATION TEMPLATE GENERATION
    # =========================================================================

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
        """Create JSON annotation template auto-generated from schema definition."""
        template_path = self.candidates_dir / f"{fragment_type}_{fragment_id}_annotation.json"

        # Generate template from Pydantic schema
        try:
            template = generate_annotation_template(fragment_type)
        except ValueError:
            # Fallback for unknown types
            template = {"type": fragment_type, "TODO": "Define schema"}

        template_path.write_text(json.dumps(template, indent=2))
        print(f"  Annotation template: {template_path.name}")

    # =========================================================================
    # COLLECTION ORCHESTRATION
    # =========================================================================

    def _create_filter_chain(self, fragment_type: str, url_patterns: list[str] | None) -> FilterChain | None:
        """Create URL filter chain based on fragment type and patterns."""
        if fragment_type == "authrequired":
            # Match login/signin/auth URLs
            return FilterChain(
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
            return FilterChain(
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
        elif url_patterns:
            # Use configurable patterns for new types (captcha_or_bot_check, etc.)
            return FilterChain([URLPatternFilter(patterns=url_patterns)])
        else:
            return None

    def _process_crawl_result(self, result, fragment_type: str) -> tuple[int, int]:
        """Process a single crawl result."""
        if not result.success:
            return 0, 0

        # Extract fragment
        fragment_html = self.extract_fragment(result.html, fragment_type)
        if not fragment_html:
            return 0, 0

        # Validate
        validation_result = self.validate_fragment(fragment_html, fragment_type)

        # Save based on validation result
        if validation_result["is_valid"]:
            self.save_fragment(fragment_html, fragment_type, result.url, validation_result)
            return 1, 0
        else:
            self.save_negative_fragment(fragment_html, fragment_type, result.url, validation_result)
            return 0, 1

    async def collect_with_deep_crawl(self, fragment_type: str, config: dict):
        """Collect fragments using deep crawling from a seed URL."""
        seed_url = config["seed_url"]
        max_pages = config.get("max_pages", 10)
        url_patterns = config.get("url_patterns")

        print(f"\n🔍 Deep crawling: {seed_url}")
        print(f"   Max pages: {max_pages}")
        if url_patterns:
            print(f"   URL patterns: {', '.join(url_patterns)}")

        # Configure URL filters
        filter_chain = self._create_filter_chain(fragment_type, url_patterns)

        # Configure deep crawling strategy
        if filter_chain:
            deep_crawl_strategy = BFSDeepCrawlStrategy(
                max_depth=2,
                max_pages=max_pages,
                include_external=False,
                filter_chain=filter_chain,
            )
        else:
            # No filter - crawl all pages
            deep_crawl_strategy = BFSDeepCrawlStrategy(
                max_depth=2,
                max_pages=max_pages,
                include_external=False,
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
                    c, r = self._process_crawl_result(result, fragment_type)
                    collected += c
                    rejected += r

        except Exception as e:
            print(f"   ❌ Error during deep crawl: {e}")

        print(f"   ✓ Collected: {collected} positive, {rejected} negative")
        return collected, rejected

    def _create_error_validation(self, status_code: int) -> dict:
        """Create validation result for error page based on status code."""
        return {
            "is_valid": False,
            "score": 0.0,
            "matched_patterns": [f"HTTP {status_code}"],
            "total_patterns": 0,
            "reason": f"HTTP error status code: {status_code}",
            "negative_type": "error_page",
        }

    async def _process_single_url(self, url: str, fragment_type: str, validation_stats: dict) -> tuple[int, int]:
        """Process a single URL: fetch, extract, validate, and save."""
        print(f"\n  Fetching: {url}")

        # Fetch page
        html, status_code = await self.fetch_page(url)
        if not html:
            print("    ✗ Failed to fetch page")
            return 0, 0

        print(f"    ✓ Fetched HTML ({len(html)} bytes, status: {status_code})")

        # Extract fragment
        fragment_html = self.extract_fragment(html, fragment_type)
        if not fragment_html:
            print("    ✗ Failed to extract fragment")
            return 0, 0

        print(f"    ✓ Extracted fragment ({len(fragment_html)} bytes)")

        # Check status code first - auto-detect error pages
        if status_code and status_code >= 400:
            error_validation = self._create_error_validation(status_code)
            print(f"    ⚠️  Error page detected (HTTP {status_code})")
            self.save_negative_fragment(fragment_html, fragment_type, url, error_validation)
            validation_stats["invalid"] += 1
            return 0, 1

        # Validate fragment
        validation_result = self.validate_fragment(fragment_html, fragment_type)
        print(f"    📊 Validation: {validation_result['reason']}")
        print(f"       Score: {validation_result['score']:.2f}")

        if not validation_result["is_valid"]:
            print(f"    ✗ Fragment rejected - {validation_result['reason']}")
            self.save_negative_fragment(fragment_html, fragment_type, url, validation_result)
            validation_stats["invalid"] += 1
            return 0, 1

        # Save fragment with validation results
        self.save_fragment(fragment_html, fragment_type, url, validation_result)
        validation_stats["valid"] += 1
        validation_stats["total_score"] += validation_result["score"]
        return 1, 0

    async def _process_sitemap_urls(self, fragment_type: str, validation_stats: dict) -> tuple[int, int, int]:
        """Process URLs discovered via sitemap."""
        # Step 1: Discover URLs from sitemaps
        discovered_urls = await self.discover_urls(fragment_type)
        domain_url_count = sum(len(urls) for urls in discovered_urls.values())

        # Step 2: Fetch and process each discovered URL
        print(f"\n📥 Fetching and validating {domain_url_count} discovered URLs...")
        print("-" * 70)

        collected = 0
        rejected = 0

        for domain, urls in discovered_urls.items():
            print(f"\n🌐 Processing {len(urls)} URLs from {domain}")

            for url in urls:
                c, r = await self._process_single_url(url, fragment_type, validation_stats)
                collected += c
                rejected += r

        return collected, rejected, domain_url_count

    async def _process_deep_crawl_configs(self, fragment_type: str, domain_configs: list[dict]) -> tuple[int, int]:
        """Process deep crawl configurations."""
        print(f"🔍 Using deep crawling from {len(domain_configs)} seed URLs...")
        print("-" * 70)

        collected = 0
        rejected = 0

        for config in domain_configs:
            c, r = await self.collect_with_deep_crawl(fragment_type, config)
            collected += c
            rejected += r

        return collected, rejected

    def _print_summary(self, total_discovered: int, total_collected: int, total_rejected: int, validation_stats: dict):
        """Print collection summary statistics."""
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

        print("=" * 70 + "\n")

    async def collect_fragments(self, categories: list[str] | None = None):
        """Collect fragments using sitemap-based URL discovery or deep crawling."""
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

            # Check collection method for this type
            domain_configs = self.domain_configs.get(fragment_type, [])
            if not domain_configs:
                continue

            # Determine collection method based on config structure
            uses_deep_crawl = "seed_url" in domain_configs[0]

            if uses_deep_crawl:
                # Use deep crawling for negative types (authrequired, errorpage, captcha, etc.)
                collected, rejected = await self._process_deep_crawl_configs(fragment_type, domain_configs)
                total_collected += collected
                total_rejected += rejected
            else:
                # Use sitemap-based discovery (traditional approach)
                collected, rejected, discovered = await self._process_sitemap_urls(fragment_type, validation_stats)
                total_collected += collected
                total_rejected += rejected
                total_discovered += discovered

        self._print_summary(total_discovered, total_collected, total_rejected, validation_stats)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect HTML fragments using Crawl4AI URL seeding",
    )
    parser.add_argument(
        "--categories",
        "-c",
        nargs="+",
        choices=[
            "recipe",
            "event",
            "pricing_table",
            "job_posting",
            "person",
            "paywall_content",
            "empty_spa_shell",
            "authrequired",
            "errorpage",
            "captcha_or_bot_check",
        ],
        help="Categories to collect (default: all). Includes negative collectors: paywall_content, empty_spa_shell, authrequired, errorpage, captcha_or_bot_check",  # noqa: E501
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    collector = FragmentCollector(project_root)

    await collector.collect_fragments(categories=args.categories)


if __name__ == "__main__":
    asyncio.run(main())
