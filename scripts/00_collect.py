import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import AsyncUrlSeeder, AsyncWebCrawler, SeedingConfig

from src.schemas import (
    ProductSchema,
    RecipeSchema,
)


class FragmentCollector:
    """Collect fragment candidates from domains using Crawl4AI URL seeding."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.candidates_dir = project_root / "data" / "seeds" / "candidates"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

        # Domain-based configuration for auto-discovery
        # Each domain has pattern, query, and target count
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
                {
                    "domain": "jobs.lever.co",
                    "pattern": "*/*",
                    "max_urls": 25,
                },
                {
                    "domain": "boards.greenhouse.io",
                    "pattern": "*/*",
                    "max_urls": 25,
                },
                {
                    "domain": "stripe.com",
                    "pattern": "*/jobs/*",
                    "max_urls": 20,
                },
                {
                    "domain": "anthropic.com",
                    "pattern": "*/careers*",
                    "max_urls": 20,
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
        Validate that fragment contains content matching schema fields.

        Returns dict with:
        - is_valid: bool
        - score: float (0-1)
        - found_fields: list of fields found
        - missing_fields: list of required fields missing
        - reason: str explanation
        """
        soup = BeautifulSoup(fragment_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        if fragment_type == "recipe":
            return self._validate_recipe(soup, text)
        elif fragment_type == "product":
            return self._validate_product(soup, text)
        elif fragment_type == "event":
            return self._validate_event(soup, text)
        elif fragment_type == "pricing_table":
            return self._validate_pricing_table(soup, text)
        elif fragment_type == "job_posting":
            return self._validate_job_posting(soup, text)
        elif fragment_type == "person":
            return self._validate_person(soup, text)
        else:
            return {
                "is_valid": True,
                "score": 0.5,
                "found_fields": [],
                "missing_fields": [],
                "reason": "Unknown type, accepting by default",
            }

    def _validate_recipe(self, soup: BeautifulSoup, text: str) -> dict:
        """Validate recipe fragment has ingredients, instructions, etc using schema patterns."""
        found_fields = []
        missing_fields = []
        score = 0.0

        # Use patterns from RecipeSchema
        validation_patterns = RecipeSchema.VALIDATION_PATTERNS

        # Check for recipe name/title (required)
        if soup.find(["h1", "h2"]) or re.search(r"recipe", text, re.IGNORECASE):
            found_fields.append("name")
            score += 0.2
        else:
            missing_fields.append("name")

        # Check for ingredients list (required) - look for measurement patterns from schema
        list_items = soup.find_all("li")
        ingredient_patterns = [
            p for p in validation_patterns if any(x in p for x in ["cup", "tablespoon", "gram", "/"])
        ]

        potential_ingredients = []
        for li in list_items:
            li_text = li.get_text(strip=True)
            if any(re.search(pattern, li_text, re.IGNORECASE) for pattern in ingredient_patterns):
                potential_ingredients.append(li_text)

        if len(potential_ingredients) >= 3:
            found_fields.append("ingredients")
            score += 0.3
        else:
            missing_fields.append("ingredients (need 3+)")

        # Check for instructions/steps (required) - use cooking verb patterns from schema
        ordered_lists = soup.find_all("ol")
        instruction_pattern = next((p for p in validation_patterns if "preheat" in p), None)

        potential_instructions = []
        if ordered_lists:
            for ol in ordered_lists:
                steps = [li.get_text(strip=True) for li in ol.find_all("li")]
                potential_instructions.extend(steps)
        else:
            # Check for paragraph-based instructions using cooking verbs
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if instruction_pattern and re.search(instruction_pattern, p_text, re.IGNORECASE):
                    potential_instructions.append(p_text)

        if len(potential_instructions) >= 3:
            found_fields.append("instructions")
            score += 0.3
        else:
            missing_fields.append("instructions (need 3+)")

        # Check for timing info (optional) - use timing pattern from schema
        time_pattern = next((p for p in validation_patterns if "min|minute" in p), None)
        if time_pattern and re.search(time_pattern, text, re.IGNORECASE):
            found_fields.append("timing_info")
            score += 0.1

        # Check for servings (optional) - use servings pattern from schema
        servings_pattern = next((p for p in validation_patterns if "serves" in p), None)
        if servings_pattern and re.search(servings_pattern, text, re.IGNORECASE):
            found_fields.append("servings")
            score += 0.1

        # Threshold: need at least name + ingredients + instructions
        is_valid = "name" in found_fields and "ingredients" in found_fields and "instructions" in found_fields

        reason = (
            f"Found {len(found_fields)} fields: {', '.join(found_fields)}"
            if is_valid
            else f"Missing required fields: {', '.join(missing_fields)}"
        )

        return {
            "is_valid": is_valid,
            "score": min(score, 1.0),
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "reason": reason,
        }

    def _validate_product(self, soup: BeautifulSoup, text: str) -> dict:
        """Validate product fragment has name, price, description, etc using schema patterns."""
        found_fields = []
        missing_fields = []
        score = 0.0

        # Use patterns from ProductSchema
        validation_patterns = ProductSchema.VALIDATION_PATTERNS

        # Check for product name (required)
        if soup.find(["h1", "h2"]) or re.search(r"product", text, re.IGNORECASE):
            found_fields.append("name")
            score += 0.3
        else:
            missing_fields.append("name")

        # Check for price (required) - use schema patterns
        price_patterns = [p for p in validation_patterns if "$" in p or "USD" in p or "price" in p.lower()]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in price_patterns):
            found_fields.append("price")
            score += 0.4
        else:
            missing_fields.append("price")

        # Check for description (optional but important)
        paragraphs = soup.find_all("p")
        if len(paragraphs) >= 1 and any(len(p.get_text(strip=True)) > 50 for p in paragraphs):
            found_fields.append("description")
            score += 0.2

        # Check for rating (optional) - use schema patterns
        rating_patterns = [p for p in validation_patterns if "rating" in p or "star" in p]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in rating_patterns):
            found_fields.append("rating")
            score += 0.1

        # Threshold: need at least name + price
        is_valid = "name" in found_fields and "price" in found_fields

        reason = (
            f"Found {len(found_fields)} fields: {', '.join(found_fields)}"
            if is_valid
            else f"Missing required fields: {', '.join(missing_fields)}"
        )

        return {
            "is_valid": is_valid,
            "score": min(score, 1.0),
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "reason": reason,
        }

    def _validate_event(self, soup: BeautifulSoup, text: str) -> dict:
        """Validate event fragment has title, date, location, etc."""
        found_fields = []
        missing_fields = []
        score = 0.0

        # Check for event title (required)
        if soup.find(["h1", "h2", "h3"]) or re.search(r"event", text, re.IGNORECASE):
            found_fields.append("title")
            score += 0.3
        else:
            missing_fields.append("title")

        # Check for datetime (required) - flexible patterns
        datetime_patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # dates like 12/15/2025
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}",  # Dec 15
            r"\d{1,2}:\d{2}\s*(AM|PM|am|pm)",  # time like 6:00 PM
            r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,",  # day of week
        ]
        if any(re.search(pattern, text) for pattern in datetime_patterns):
            found_fields.append("datetime")
            score += 0.4
        else:
            missing_fields.append("datetime")

        # Check for location/venue (optional but common)
        location_indicators = [
            r"location:",
            r"venue:",
            r"online",
            r"virtual",
            r"\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)",
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in location_indicators):
            found_fields.append("location")
            score += 0.2

        # Check for organizer/attendees (optional)
        if re.search(r"(organiz|host|by)\s*:", text, re.IGNORECASE) or re.search(
            r"\d+\s*(attendee|going|interested)", text, re.IGNORECASE
        ):
            found_fields.append("organizer_info")
            score += 0.1

        # Threshold: need at least title + datetime
        is_valid = "title" in found_fields and "datetime" in found_fields

        reason = (
            f"Found {len(found_fields)} fields: {', '.join(found_fields)}"
            if is_valid
            else f"Missing required fields: {', '.join(missing_fields)}"
        )

        return {
            "is_valid": is_valid,
            "score": min(score, 1.0),
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "reason": reason,
        }

    def _validate_pricing_table(self, soup: BeautifulSoup, text: str) -> dict:
        """Validate pricing table has multiple plans with prices and features."""
        found_fields = []
        missing_fields = []
        score = 0.0

        # Check for pricing indicators
        price_patterns = [
            r"\$\d+",
            r"\d+\s*(USD|EUR|GBP)",
            r"(free|trial)",
            r"contact\s+sales",
            r"/month|/year|monthly|yearly|annually",
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in price_patterns):
            found_fields.append("pricing_info")
            score += 0.4
        else:
            missing_fields.append("pricing_info")

        # Check for multiple plans (look for plan names like "Basic", "Pro", "Enterprise")
        plan_indicators = soup.find_all(["h2", "h3", "h4"])
        if len(plan_indicators) >= 2:
            found_fields.append("multiple_plans")
            score += 0.3
        else:
            missing_fields.append("multiple_plans (need 2+)")

        # Check for features list
        list_items = soup.find_all("li")
        if len(list_items) >= 5:
            found_fields.append("features")
            score += 0.3

        # Threshold: need pricing_info + multiple_plans
        is_valid = "pricing_info" in found_fields and "multiple_plans" in found_fields

        reason = (
            f"Found {len(found_fields)} fields: {', '.join(found_fields)}"
            if is_valid
            else f"Missing required fields: {', '.join(missing_fields)}"
        )

        return {
            "is_valid": is_valid,
            "score": min(score, 1.0),
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "reason": reason,
        }

    def _validate_job_posting(self, soup: BeautifulSoup, text: str) -> dict:
        """Validate job posting has title, company, location (simplified listing format)."""
        found_fields = []
        missing_fields = []
        score = 0.0

        # Check for job title (required)
        if soup.find(["h1", "h2"]):
            found_fields.append("title")
            score += 0.4
        else:
            missing_fields.append("title")

        # Check for company name
        if re.search(r"company:", text, re.IGNORECASE) or soup.find(class_=lambda x: x and "company" in x.lower()):
            found_fields.append("company")
            score += 0.3
        else:
            # Sometimes company is implicit if it's on their domain
            found_fields.append("company")
            score += 0.2

        # Check for location
        location_patterns = [
            r"(remote|hybrid|on-?site)",
            r"(location|based in):",
            r"[A-Z][a-z]+,\s*[A-Z]{2}",  # City, ST format
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in location_patterns):
            found_fields.append("location")
            score += 0.2

        # Check for employment type
        if re.search(r"(full-?time|part-?time|contract|intern)", text, re.IGNORECASE):
            found_fields.append("employment_type")
            score += 0.1

        # Threshold: need at least title
        is_valid = "title" in found_fields

        reason = (
            f"Found {len(found_fields)} fields: {', '.join(found_fields)}"
            if is_valid
            else f"Missing required fields: {', '.join(missing_fields)}"
        )

        return {
            "is_valid": is_valid,
            "score": min(score, 1.0),
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "reason": reason,
        }

    def _validate_person(self, soup: BeautifulSoup, text: str) -> dict:
        """Validate person profile has name, title/role, and contact or bio."""
        found_fields = []
        missing_fields = []
        score = 0.0

        # Check for name (required) - usually in h1, h2, or h3
        headings = soup.find_all(["h1", "h2", "h3"])
        if headings:
            found_fields.append("name")
            score += 0.4
        else:
            missing_fields.append("name")

        # Check for title/role
        title_patterns = [
            r"(professor|dr\.|phd|researcher|engineer|scientist|director|manager)",
            r"(title|position|role):",
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in title_patterns):
            found_fields.append("title")
            score += 0.3

        # Check for bio/description
        paragraphs = soup.find_all("p")
        if len(paragraphs) >= 1 and any(len(p.get_text(strip=True)) > 100 for p in paragraphs):
            found_fields.append("bio")
            score += 0.2

        # Check for contact info (email, phone, or social links)
        contact_patterns = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # email
            r"linkedin\.com",
            r"\(\d{3}\)\s*\d{3}-\d{4}",  # phone
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in contact_patterns):
            found_fields.append("contact")
            score += 0.1

        # Threshold: need at least name + (title OR bio)
        is_valid = "name" in found_fields and ("title" in found_fields or "bio" in found_fields)

        reason = (
            f"Found {len(found_fields)} fields: {', '.join(found_fields)}"
            if is_valid
            else f"Missing required fields: {', '.join(missing_fields)}"
        )

        return {
            "is_valid": is_valid,
            "score": min(score, 1.0),
            "found_fields": found_fields,
            "missing_fields": missing_fields,
            "reason": reason,
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
                "found_fields": validation_result["found_fields"],
                "missing_fields": validation_result["missing_fields"],
            },
        }
        metadata_path = self.candidates_dir / f"{fragment_type}_{fragment_id}.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # Create annotation template
        self._create_annotation_template(fragment_type, fragment_id)

        print(f"✓ Saved {fragment_type} fragment: {fragment_id} (score: {validation_result['score']:.2f})")
        print(f"  Source: {source_url}")
        print(f"  Found fields: {', '.join(validation_result['found_fields'])}")
        print(f"  Files: {html_path.name}, {metadata_path.name}")

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

            # Step 1: Discover URLs from sitemaps
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
        print(f"Collected: {total_collected} fragments")
        print(f"Rejected: {total_rejected} fragments")
        if total_collected > 0:
            avg_score = validation_stats["total_score"] / total_collected
            print(f"Average quality score: {avg_score:.2f}")
            success_rate = (total_collected / total_discovered) * 100
            print(f"Success rate: {success_rate:.1f}%")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Review fragments in data/seeds/candidates/")
        print("2. Fill in annotation templates (*_annotation.json)")
        print("3. Use streamlit app: streamlit run scripts/label_app.py")
        print("=" * 70 + "\n")


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
        choices=["recipe", "product", "event", "pricing_table", "job_posting", "person"],
        help="Categories to collect (default: all)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    collector = FragmentCollector(project_root)

    await collector.collect_fragments(categories=args.categories)


if __name__ == "__main__":
    asyncio.run(main())
