# Phase 1: Fine-Tuning Dataset Generation (REVISED)

## Executive Summary

**Problem Identified**: The initial approach optimized for web page quality rather than extraction task robustness. We collected full pages and filtered for "clean" content, when the task requires teaching a model to extract structured data fragments from noisy, messy HTML.

**Core Paradigm Shift**:
- FROM: Crawl pages → filter for quality → hope schema emerges
- TO: Define schema → collect fragments with noise → expand deliberately

**Goal**: Generate 5,000 training examples teaching a small language model (Qwen 0.6B) to:
1. Identify data-carrying fragments within noisy HTML
2. Ignore irrelevant surrounding elements (navbars, ads, scripts, footers)
3. Extract structured JSON following a predefined schema
4. Handle edge cases (error pages, auth walls, malformed HTML)

---

## Part 1: Schema-First Design

### 1.1 Define Fragment Types and Schemas

**Critical First Step**: Define the extraction schema BEFORE data collection. The schema drives what we collect, not the reverse.

**Schema Philosophy**: Simplified for small model (Qwen 0.6B) training based on real-world data analysis. See `SCHEMA_REVIEW.md` for detailed validation against actual websites.

#### Tier 1: Start Here (Simplest, Most Common) - 3 types

**1. Product Card** ✅ TIER 1
```json
{
  "type": "product",
  "name": "string",
  "brand": "string | null",
  "price": {
    "current": float,
    "original": float | null,
    "currency": "string"
  },
  "rating": {
    "score": float,
    "review_count": int
  } | null,
  "description": "string | null",
  "availability": "in_stock" | "out_of_stock" | "pre_order" | "limited" | null,
  "image_url": "string | null"
}
```
**Complexity**: 7 fields, 2 nesting levels | **Changes**: Added `brand`, removed `discount_percent` (calculable), removed `rating.max` (always 5), removed `product_id` (obfuscated)

**2. Review Block** ✅ TIER 1
```json
{
  "type": "review",
  "reviewer_name": "string",
  "reviewer_verified": bool | null,
  "rating": float,
  "title": "string | null",
  "date": "string",
  "body": "string",
  "helpful_count": int | null
}
```
**Complexity**: 6 fields, 1 nesting level | **Changes**: Flattened `reviewer` object, removed `avatar_url`, removed `review_id`, removed `rating.max`

**3. Recipe Card** ✅ TIER 1
```json
{
  "type": "recipe",
  "name": "string",
  "description": "string | null",
  "author": "string | null",
  "prep_time": "string | null",
  "cook_time": "string | null",
  "total_time": "string | null",
  "servings": "string | null",
  "ingredients": ["string"],
  "instructions": ["string"],
  "rating": {
    "score": float,
    "review_count": int
  } | null
}
```
**Complexity**: 9 fields, 2 nesting levels | **Changes**: Time fields as strings ("5 min", "PT5M", "1 hour"), removed `rating.max`, removed `date_published`

#### Tier 2: Add Next (Moderate Complexity) - 2 types

**4. Event Listing** ⚠️ TIER 2
```json
{
  "type": "event",
  "title": "string",
  "datetime": "string",
  "location": "string | null",
  "venue_name": "string | null",
  "price": "string | null",
  "organizer": "string | null",
  "attendee_count": int | null,
  "description": "string | null",
  "event_type": "online" | "in_person" | null
}
```
**Complexity**: 8 fields, 1 nesting level | **Changes**: Flattened `venue`, single `datetime` (not ISO8601), price as string ("Free", "$25"), added `organizer`, `attendee_count`, `event_type`, removed `category`

**5. Pricing Table** ⚠️ TIER 2
```json
{
  "type": "pricing_table",
  "plans": [
    {
      "name": "string",
      "price": "string",
      "price_amount": float | null,
      "currency": "string | null",
      "billing_period": "month" | "year" | "one_time" | null,
      "features": ["string"],
      "description": "string | null"
    }
  ]
}
```
**Complexity**: 6 fields per plan, 2 nesting levels | **Changes**: Removed global `trial_period`, added `price` string field, removed `features.included/not_included` split, removed `highlighted`, `badge`, `contact_sales`, `cta_url`

#### Tier 3: Consider Later (Lower Priority) - 2 types

**6. Job Posting (Listing Fragment Only)** ⚠️ TIER 3
```json
{
  "type": "job_posting",
  "title": "string",
  "company": "string",
  "location": "string",
  "department": "string | null",
  "posted_date": "string | null",
  "employment_type": "string | null",
  "description": "string | null"
}
```
**Complexity**: 7 fields, 1 nesting level | **Changes**: CRITICAL - Focus on listing fragments (not full job pages). Flattened `company`, flattened `location`, removed `salary` (70%+ listings don't show), removed `requirements`, `benefits`, `experience_required`, added `posted_date`, `department`

**7. Contact/Person Card** ⚠️ TIER 3
```json
{
  "type": "person",
  "name": "string",
  "title": "string | null",
  "bio": "string | null",
  "email": "string | null",
  "phone": "string | null",
  "linkedin": "string | null",
  "image_url": "string | null"
}
```
**Complexity**: 6 fields, 1 nesting level | **Changes**: Flattened `contact` and `social` objects, removed `twitter`, `github` | **Note**: Rare in modern sites (privacy, GDPR)

#### Negative Fragment Types (3 types)

These teach the model what NOT to extract:

**9. Error Page**
```json
{
  "type": "error_page",
  "error_code": int,
  "message": "string",
  "description": "string"
}
```

**10. Auth Required**
```json
{
  "type": "auth_required",
  "message": "string",
  "description": "string",
  "content_available": false
}
```

**11. Empty SPA Shell**
```json
{
  "type": "empty_shell",
  "framework": "react" | "vue" | "angular" | null,
  "content_available": false,
  "reason": "client_side_rendering"
}
```

### 1.2 Schema Design Principles (Updated for Small Models)

**Core Principles**:
1. **Type Discriminators**: Every JSON includes `"type"` field for classification
2. **Nullable Fields**: Use `null` for missing/unavailable data (don't hallucinate)
3. **Minimal Nesting**: Maximum 2 levels deep (preferably 1 level)
4. **String-First for Variable Formats**: Use strings where real-world formatting varies (times, dates, prices)
5. **Consistent Naming**: Use snake_case, descriptive field names
6. **80% Rule**: Focus on fields present in 80%+ of real examples
7. **No Redundancy**: Remove calculable values and always-constant fields
8. **Validation Ready**: Schema should be validatable with JSON Schema/Pydantic

**Real-World Validation**: All schemas validated against actual websites (Stripe, Shopify, Notion, Meetup, LinkedIn, etc.) and Schema.org 2025 standards. See `SCHEMA_REVIEW.md` for detailed analysis.

**Complexity Budget for Qwen 0.6B**:
- **Simple** (1-2 nesting levels, 5-8 fields): Product, Review, Recipe, Event, Job, Person
- **Moderate** (2 levels, 6-8 fields per nested item): Pricing Table
- **Avoid** (3+ levels, 12+ fields): Over-engineered schemas that small models struggle with

**Deliverable**: `schema/fragment_types.json` defining 10 fragment types (7 positive + 3 negative) with JSON Schema validation rules.

### 1.3 Schema.org Alignment Strategy

**Question**: Are we using Schema.org as reference?
**Answer**: **Yes, but with pragmatic simplifications for small model training.**

#### What We Take from Schema.org (2025 Standards)

✅ **Field naming conventions**: Use standard names (`name`, `description`, `author`, `datePublished`)
✅ **Required fields guidance**: Learn from what Schema.org marks as required
✅ **Type mappings**: Our types align with Schema.org types where applicable
✅ **Validation baseline**: Ensure our schemas don't conflict with standards

**Schema.org Alignment**:
- Product Card → [Schema.org Product](https://schema.org/Product)
- Recipe Card → [Schema.org Recipe](https://schema.org/Recipe)
- Job Posting → [Schema.org JobPosting](https://schema.org/JobPosting)
- Review Block → [Schema.org Review](https://schema.org/Review)
- Event Listing → [Schema.org Event](https://schema.org/Event)
- Person Card → [Schema.org Person](https://schema.org/Person)
- Pricing Table → No direct equivalent (UI component, not semantic type)

#### Where We Deviate (And Why)

**Schema.org is optimized for**: SEO, search engines, web crawlers, semantic web
**Our schemas are optimized for**: Small model (Qwen 0.6B) fine-tuning on noisy HTML fragments

| Aspect | Schema.org | Our Approach | Reason |
|--------|------------|--------------|--------|
| **Nesting depth** | 3-4 levels allowed | 1-2 levels max | Small models struggle with deep nesting |
| **Time formats** | ISO 8601 (PT20M) | Strings ("20 min") | Real sites use varied formats |
| **Price formats** | Structured offers | Strings ("$25", "Free") | Handles "Contact sales", "Sold out" |
| **Rating scale** | Include min/max/best/worst | Just score + count | Max always 5, redundant |
| **Granularity** | Full page semantics | Fragment extraction | We extract UI components from noisy HTML |
| **Required fields** | Many required for SEO | More nullable fields | Real fragments often incomplete |

#### Example: Recipe Comparison

**Schema.org Recipe** (full standard):
```json
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Chocolate Chip Cookies",
  "prepTime": "PT15M",              // ISO 8601: 15 minutes
  "cookTime": "PT12M",              // ISO 8601: 12 minutes
  "totalTime": "PT27M",
  "recipeYield": "24 cookies",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 4.8,
    "bestRating": "5",
    "worstRating": "1",
    "ratingCount": 342
  },
  "author": {
    "@type": "Person",
    "name": "Julia Baker"
  }
}
```

**Our Recipe Schema** (simplified for small models):
```json
{
  "type": "recipe",
  "name": "Chocolate Chip Cookies",
  "prep_time": "15 min",            // String: handles "15 min", "PT15M", "1 hour"
  "cook_time": "12 min",            // Often missing in real fragments
  "total_time": "27 min",
  "servings": "24 cookies",
  "rating": {
    "score": 4.8,                   // No min/max/best/worst (always 5/1)
    "review_count": 342
  },
  "author": "Julia Baker",          // String, not nested Person object
  "description": "string | null",
  "ingredients": ["string"],
  "instructions": ["string"]
}
```

**Key simplifications**:
1. Times as strings (real sites use "15 min", "PT15M", or "1 hour" inconsistently)
2. Author as string (not nested Person object - reduces nesting)
3. Rating simplified (removed bestRating/worstRating - always 5/1)
4. More nullable fields (real fragments often incomplete)

#### Benefits of This Hybrid Approach

1. **Pre-training potential**: Models could be pre-trained on Schema.org markup, then fine-tuned on our data
2. **Standard compliance**: Our output JSONs can be converted to Schema.org format if needed
3. **Real-world validation**: Schema.org reflects actual web usage patterns (but we adapt to reality)
4. **Future extensibility**: Easy to add Schema.org fields later without breaking schemas
5. **Small model feasibility**: Simplified structures that Qwen 0.6B can actually learn

#### Validation Against Schema.org

See `SCHEMA_REVIEW.md` for detailed analysis comparing our schemas to:
- Schema.org 2025 standards
- Real-world implementations (Stripe, Shopify, Notion, Meetup, LinkedIn, Goodreads)
- Google Structured Data guidelines

**Bottom line**: We use Schema.org as a **foundation**, but simplify based on **real-world HTML fragments** and **small model constraints**.

---

## Part 2: Seed Data Collection Strategy

### 2.1 Fragment Identification (Not Page Collection)

**Key Principle**: We need HTML snippets containing data fragments embedded in noise, not full pages.

#### Option A: Extract Fragments from Existing 469 Pages

**Advantage**: Reuse existing crawled data
**Approach**:
1. Parse each of the 469 HTML pages
2. Identify candidate fragments using heuristics:
   - Product cards: elements with price + title + description patterns
   - Event listings: elements with datetime + location patterns
   - Contact blocks: elements with email/phone patterns
   - Pricing tables: grid/flex layouts with multiple price blocks
   - Reviews: elements with rating + reviewer + body patterns
3. Extract fragment WITH surrounding noise (500-2000 tokens context)
4. Manually label 5-10 best examples per fragment type
5. Write expected JSON for each example

**Expected Yield**: 50-80 seed examples across 8 positive types

#### Option B: Curate Fragments from Targeted Sources

**Advantage**: Higher quality, more diverse fragments
**Approach**:
1. For each fragment type, identify 3-5 websites with good examples:
   - Products: Amazon, Etsy, Shopify stores
   - Events: Eventbrite, Meetup, concert venues
   - Recipes: AllRecipes, Serious Eats, food blogs
   - Jobs: LinkedIn, Indeed, company career pages
   - Reviews: Amazon, Yelp, G2, TripAdvisor
   - Pricing: SaaS landing pages, subscription services
2. Scrape/crawl specific pages containing fragments
3. Extract fragments with 500-2000 tokens of surrounding noise
4. Manually write expected JSON for each
5. Include various HTML quality levels (clean, messy, malformed)

**Expected Yield**: 80-100 seed examples across 8 positive types

#### Recommended: Tiered Hybrid Approach

**Phase 1 - Tier 1 Types (Week 1-2)**:
1. Focus on **Product, Review, Recipe** only (3 types)
2. Start with Option A (extract from existing 469 pages)
3. Supplement with Option B for quality/diversity
4. Target: **30-40 seed examples** (10-15 per Tier 1 type)
5. **Decision point**: Validate pilot before proceeding

**Phase 2 - Tier 2 Types (Week 3)** - Only if Phase 1 succeeds:
6. Add **Event, Pricing** (2 additional types)
7. Use hybrid approach (existing pages + targeted scraping)
8. Target: **50-60 total seed examples** (10-12 per type)

**Phase 3 - Tier 3 Types (Week 4)** - Only if needed:
9. Evaluate if **Job, Person** types are worth including
10. Target: **70-80 total seed examples** if all 7 types included

### 2.2 Negative Example Collection

**Critical for Robustness**: Model must learn what NOT to extract.

**Sources**:
- Error pages: Trigger 404s, 500s on various sites
- Auth walls: Paywall sites (NYTimes, Medium), login-required content
- SPA shells: React/Vue/Angular apps with empty initial HTML

**Target**: 10-15 negative examples across 3 negative types

### 2.3 Noise Characteristics

**What is "noise"?** Elements surrounding the data fragment that should be ignored:

- Navigation bars (header/footer links)
- Sidebar advertisements
- Related content sections
- Cookie consent banners
- Social sharing buttons
- Tracking scripts
- Analytics pixels
- Comments sections
- Newsletter popups

**Noise Guidelines**:
- **Minimum context**: 200 tokens (fragment might be isolated)
- **Optimal context**: 500-2000 tokens (fragment + moderate noise)
- **Maximum context**: 8000 tokens (dense page with multiple fragments)

**Critical**: Do NOT clean or sanitize HTML. Preserve:
- Malformed tags (missing quotes, unclosed elements)
- Inline styles and scripts
- Inconsistent formatting (mixed indentation, minified sections)
- Framework-specific attributes (data-*, ng-*, v-*)

### 2.4 Manual Annotation Process

For each seed example:

1. **Extract HTML snippet** (fragment + noise, 200-8000 tokens)
2. **Write expected JSON** following schema exactly
3. **Validate JSON** against JSON Schema definitions
4. **Document edge cases**: missing fields, unusual structures, ambiguities
5. **Quality check**: Can a human consistently extract this JSON from HTML?

**Deliverable**: `data/seeds/` directory with:
- `{fragment_type}_{id}.html` - HTML snippets
- `{fragment_type}_{id}.json` - Expected JSON outputs
- `seeds_manifest.jsonl` - Metadata for all seed examples

**Success Criteria**:
- 80-120 seed examples total
- 10-15 examples per fragment type (8 positive + 3 negative)
- All JSONs validate against schema
- HTML ranges 200-8000 tokens
- Diverse noise levels (low, medium, high)
- Mix of HTML quality (clean, messy, malformed)

---

## Part 3: Synthetic Augmentation Strategy

### 3.1 Augmentation Goals

**Purpose**: Generate variations that teach the model to:
1. Handle structural HTML variations while preserving semantic content
2. Ignore irrelevant attributes and styling
3. Locate fragments within varying levels of noise
4. Parse malformed HTML gracefully

**Non-Goals**: Do NOT augment to:
- Change the semantic content (expected JSON must remain identical)
- Generate unrealistic HTML that wouldn't occur in the wild
- Introduce noise patterns that mislead rather than train

### 3.2 Augmentation Techniques

#### Tier 1: High-Value Augmentations (Always Apply)

**1. Structural Noise Injection**
```python
# Add 1-4 noise elements around the fragment
noise_templates = [
    '<nav class="main-nav">...</nav>',
    '<div class="sidebar-ad"><img src="ad.jpg"/></div>',
    '<div class="cookie-banner">...</div>',
    '<script>analytics.track(...);</script>',
    '<footer>...</footer>'
]
# Insert before/after fragment, or wrap fragment in containers
```

**2. Wrapper Nesting Variations**
```python
# Add 0-3 wrapper divs around the fragment
variations = [
    fragment,  # no wrapper
    f'<div class="container">{fragment}</div>',  # 1 wrapper
    f'<div class="page"><div class="content">{fragment}</div></div>',  # 2 wrappers
    f'<div id="app"><div class="wrapper"><section>{fragment}</section></div></div>'  # 3 wrappers
]
```

**3. Attribute Randomization**
```python
# Add random but realistic attributes (20-30% of elements)
# - Random class names (layout-*, component-*, ui-*)
# - Random IDs (elem-{uuid})
# - Data attributes (data-testid, data-component, data-track)
# - ARIA attributes (aria-label, aria-describedby)
```

**4. Semantic Tag Swapping**
```python
# Swap functionally equivalent tags
equivalents = {
    'div': ['section', 'article', 'aside'],
    'span': ['em', 'i', 'label'],
    'ul': ['div with role="list"'],
    'button': ['a with role="button"']
}
# Swap 10-20% of elements
```

**5. Whitespace and Formatting Variations**
```python
variations = [
    prettify(html, indent=2),      # pretty printed
    prettify(html, indent=4),      # wider indentation
    minify(html),                   # minified
    partial_minify(html, ratio=0.5) # half minified, half pretty
]
```

**6. HTML Comment Injection**
```python
# Add 2-8 realistic developer comments
comments = [
    '<!-- TODO: refactor this component -->',
    '<!-- Legacy code - do not modify -->',
    '<!-- Generated by CMS -->',
    '<!-- End of section -->',
    '<!-- Analytics snippet -->'
]
```

**Expected Variations per Seed**: 40-60 variations using Tier 1 techniques

#### Tier 2: Medium-Value Augmentations (Test in Ablation)

**7. Noise Level Scaling**
```python
noise_levels = {
    'low': 1-2 noise elements (200-800 tokens total),
    'medium': 3-5 noise elements (800-2000 tokens total),
    'high': 6-10 noise elements (2000-8000 tokens total)
}
# Generate examples at each noise level
```

**8. Element Reordering (within fragment)**
```python
# Reorder sibling elements that don't affect semantics
# E.g., in a product card, swap position of price and rating
# ONLY reorder when order is not semantically meaningful
```

**9. Inline Style Injection**
```python
# Add inline styles (10-15% of elements)
# Focus on layout/presentation styles that should be ignored
styles = ['style="display: flex;"', 'style="margin: 20px;"', 'style="color: #333;"']
```

**Expected Additional Variations**: +10-20 per seed

#### Tier 3: Experimental Augmentations (Ablation Only)

**10. Controlled HTML Corruption**
```python
# Introduce realistic parsing issues (5-10% probability)
corruptions = [
    'missing closing tag (browser auto-closes)',
    'unquoted attribute values',
    'mismatched heading tags (h2 → h3)',
    'orphaned closing tags (ignored by parser)'
]
# MUST ensure: BeautifulSoup can still parse successfully
```

**11. Framework-Specific Attributes**
```python
# Add framework signatures (React, Vue, Angular)
attributes = {
    'react': ['data-reactid', 'data-react-root'],
    'vue': ['v-if', 'v-for', 'v-bind:class'],
    'angular': ['ng-if', 'ng-repeat', 'ng-class']
}
```

**Expected Additional Variations**: +5-10 per seed (only if ablation shows value)

### 3.3 Augmentation Pipeline Architecture

```python
class AugmentationPipeline:
    def __init__(self, seed_example):
        self.base_html = seed_example['html']
        self.base_json = seed_example['json']  # MUST remain unchanged

    def generate_variations(self, target_count=50):
        variations = []

        # Tier 1: Always apply (40-60 variations)
        for _ in range(target_count):
            html = self.base_html

            # Apply random combination of Tier 1 techniques
            html = self.add_wrapper_nesting(html, depth=random.randint(0, 3))
            html = self.inject_noise(html, count=random.randint(1, 4))
            html = self.randomize_attributes(html, probability=0.25)
            html = self.swap_semantic_tags(html, probability=0.15)
            html = self.vary_whitespace(html)
            html = self.inject_comments(html, count=random.randint(2, 8))

            # Validate
            assert self.parse_and_extract(html) == self.base_json, "JSON changed!"
            assert len(tokenize(html)) in range(200, 8000), "Token count out of range"

            variations.append({
                'html': html,
                'json': self.base_json  # Unchanged
            })

        return variations
```

### 3.4 Validation Requirements

Every generated variation MUST pass:

1. **Schema Validation**: JSON matches fragment type schema exactly
2. **Invariance Check**: Expected JSON identical to seed example's JSON
3. **Parseability**: BeautifulSoup can parse without crashing
4. **Token Range**: 200-8000 tokens (fragment + noise)
5. **Deduplication**: Not identical to another variation (use hash)

**Automated Validation Script**: `scripts/validate_variations.py`

### 3.5 Scaling Strategy

**Pilot Phase (Week 3)**:
- Select 10 seed examples (diverse fragment types)
- Generate 50 variations each = 500 pilot examples
- Train small model (Qwen 0.6B) on pilot
- Evaluate on held-out real seed examples

**Intermediate Scale (Week 4-5)** - Only if pilot validates:
- Use all 80-120 seed examples
- Generate 40-60 variations each = 3,200-7,200 examples
- Split: 70% train / 15% val / 15% test (split seeds BEFORE augmenting)
- Target: ~5,000 training examples

**Data Split Protocol**:
```python
# Split SEED examples first
train_seeds, val_seeds, test_seeds = split_seeds(seeds, ratios=[0.7, 0.15, 0.15])

# Augment ONLY training seeds
train_examples = augment_seeds(train_seeds, variations_per_seed=50)

# Val/test remain REAL (no augmentation)
val_examples = val_seeds  # 12-18 real examples
test_examples = test_seeds  # 12-18 real examples
```

**Critical Rules**:
- NEVER augment validation or test sets
- Validation/test MUST be real, unseen HTML
- Split seeds BEFORE any augmentation
- Each variation of the same seed has identical expected JSON

---

## Part 4: Dataset Format and Infrastructure

### 4.1 Training Data Format

**File Structure**:
```
data/
  seeds/
    products/
      product_001.html
      product_001.json
      ...
    events/
    recipes/
    ...
  augmented/
    train/
      train_000001.jsonl
      train_000002.jsonl
      ...
    val/
      val_000001.jsonl
      ...
    test/
      test_000001.jsonl
      ...
  metadata/
    seed_manifest.json        # Metadata for all seeds
    augmentation_config.json  # Augmentation parameters used
    dataset_stats.json        # Statistics and validation results
```

**JSONL Format** (each line):
```json
{
  "example_id": "train_003847",
  "seed_id": "product_042",
  "fragment_type": "product",
  "input_html": "<div class='page-wrapper'><nav>...</nav><div class='product-card'>...</div></div>",
  "expected_output": {
    "type": "product",
    "name": "Wireless Headphones",
    "price": {...},
    ...
  },
  "metadata": {
    "augmentation_techniques": ["wrapper_nesting", "noise_injection", "attribute_randomization"],
    "token_count": 1847,
    "noise_level": "medium"
  }
}
```

### 4.2 Chat Format Conversion

For instruction fine-tuning (e.g., HuggingFace TRL):

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a specialized HTML data extraction assistant. Extract structured information from HTML into JSON. Focus on the main data-carrying fragment and ignore navigation, ads, scripts, and other noise."
    },
    {
      "role": "user",
      "content": "Extract structured data from the following HTML:\n\n<div class='page-wrapper'><nav>...</nav><div class='product-card'>...</div></div>"
    },
    {
      "role": "assistant",
      "content": "{\"type\": \"product\", \"name\": \"Wireless Headphones\", ...}"
    }
  ]
}
```

### 4.3 Validation and Quality Metrics

**Automated Checks** (run on full dataset):

1. **Schema Compliance**: 100% of JSONs validate against schemas
2. **HTML Parseability**: 100% parse successfully with BeautifulSoup
3. **Token Distribution**:
   - Min: 200 tokens
   - Median: 800-1500 tokens
   - Max: 8000 tokens
4. **Fragment Type Coverage**: At least 400 examples per positive type
5. **Negative Example Ratio**: 10-15% negative examples
6. **Deduplication**: <1% exact duplicates
7. **Augmentation Diversity**: <30% of variations share identical augmentation technique sets

**Manual Quality Checks** (sample 100 random examples):

1. JSON accurately represents HTML content
2. Noise elements properly ignored in extraction
3. No hallucinated data (missing fields correctly set to null)
4. HTML looks realistic (not obviously synthetic)
5. Structural variations preserve semantics

**Deliverable**: `reports/dataset_quality_report.md` with validation results and statistics

---

## Part 5: Execution Timeline (Tiered Approach)

### Week 1-2: Tier 1 Schema & Seeds (Product, Review, Recipe)
**Week 1**:
- Define Tier 1 fragment type schemas (3 types) with JSON Schema validation
- Build seed annotation tools (HTML viewer + JSON editor)
- Extract Tier 1 seed candidates from existing 469 pages
- Manual review and refinement of 15-20 Tier 1 seeds

**Week 2**:
- Complete Tier 1 seed extraction (target: 30-40 total)
- Supplement with targeted scraping for quality/diversity
- Curate negative examples (error pages, auth walls, SPAs: 5-10)
- Finalize Tier 1 seed dataset with manual JSON annotation
- **Decision Point**: Validate Tier 1 seeds before proceeding

### Week 3: Tier 1 Pilot Augmentation
- Implement Tier 1 augmentation pipeline
- Generate pilot dataset (10 Tier 1 seeds × 50 variations = 500 examples)
- Validate pilot dataset (automated checks + manual review)
- Quick training test: Does augmented data help? (Preview of Task B)
- **Decision Point**: If pilot fails, revise augmentation strategy; if succeeds, proceed to Tier 2

### Week 4: Tier 2 Seeds & Augmentation (Event, Pricing) - If Tier 1 Succeeds
- Define Tier 2 schemas (2 types)
- Extract/curate Tier 2 seeds (target: +20 seeds, 50-60 total)
- Generate Tier 2 augmentations
- Combined dataset: ~2,500-3,000 examples (all Tier 1 + Tier 2)
- **Decision Point**: Evaluate if Tier 3 types are needed

### Week 5: Full Dataset Generation & Validation
- Optionally add Tier 3 types (Job, Person) if needed
- Generate full augmented dataset from all seeds
- Target: ~5,000 training examples + real val/test sets
- Run comprehensive validation suite
- Generate dataset statistics and quality report
- Convert to chat format for HuggingFace training
- Push to HuggingFace Hub

**Total Duration**: 5 weeks (flexible based on tier performance)

**Key Decision Points**:
- End of Week 2: Do we have sufficient Tier 1 seed coverage? (need 30+ seeds)
- End of Week 3: Does Tier 1 pilot augmentation improve over baseline? (CRITICAL - if no, stop and revise)
- End of Week 4: Should we add Tier 3 types or scale up Tier 1+2? (based on model capacity)
- End of Week 5: Does full dataset meet quality thresholds? (if no, regenerate problem subsets)

---

## Part 6: Success Criteria

### Dataset Quality Metrics

**Coverage** (Tiered):
- [ ] **Tier 1 (Minimum)**: 3 fragment types (Product, Review, Recipe) with schemas defined
- [ ] **Tier 2 (Target)**: 5 fragment types (+Event, Pricing)
- [ ] **Tier 3 (Optional)**: 7 fragment types (+Job, Person)
- [ ] **Negative types**: 3 types (error, auth_required, empty_shell)
- [ ] **Seeds**: 30-80 manually annotated seed examples (depending on tiers)
- [ ] **Training**: 3,000-5,000 augmented examples (depending on tiers)
- [ ] **Validation**: 10-15 real validation examples (no augmentation)
- [ ] **Test**: 10-15 real test examples (no augmentation)

**Quality**:
- [ ] 100% schema compliance (all JSONs validate)
- [ ] 100% HTML parseability (no parser crashes)
- [ ] Token distribution: 95% within 200-8000 range
- [ ] Manual review: 90%+ accuracy on 100-example sample
- [ ] Augmentation diversity: <30% duplicate technique combinations
- [ ] Real-world validation: Schemas match actual website patterns

**Robustness**:
- [ ] 3-7 positive fragment types covered (depending on tier)
- [ ] 3 negative types (errors, auth walls, empty shells)
- [ ] Noise level variation (low/medium/high)
- [ ] HTML quality variation (clean/messy/malformed)
- [ ] Fragment complexity variation (simple/moderate/complex)

### Deliverables Checklist

- [ ] `schema/fragment_types.json` - JSON Schema definitions for 10 types (7 positive + 3 negative)
- [ ] `SCHEMA_REVIEW.md` - Real-world validation analysis
- [ ] `data/seeds/` - 30-80 manually annotated seed examples (tiered)
- [ ] `data/augmented/train/` - 3,000-5,000 training examples (JSONL)
- [ ] `data/augmented/val/` - 10-15 real validation examples (JSONL)
- [ ] `data/augmented/test/` - 10-15 real test examples (JSONL)
- [ ] `data/chat_format/` - Chat-formatted versions for HuggingFace training
- [ ] `scripts/validate_dataset.py` - Automated validation suite
- [ ] `reports/dataset_quality_report.md` - Quality metrics and statistics
- [ ] HuggingFace Hub dataset published with README

---

## Part 7: Key Principles (Summary)

1. **Schema-First**: Define extraction targets before collecting data
2. **Fragment-Focused**: Extract data-carrying snippets, not full pages
3. **Noise is Signal**: Surrounding noise teaches the model what to ignore
4. **Negative Examples Matter**: Error pages and auth walls prevent hallucination
5. **Augmentation Preserves Semantics**: HTML varies, but JSON must remain identical
6. **Real Validation**: Val/test sets must be real, unaugmented examples
7. **Split Before Augment**: Prevent data leakage by splitting seeds first
8. **Validate Continuously**: Every stage has automated quality checks

---

## Appendix A: Differences from Original Plan

| Aspect | Original Plan | Revised Plan |
|--------|---------------|--------------|
| **Data Unit** | Full web pages (4K-128K tokens) | HTML fragments with noise (200-8K tokens) |
| **Schema** | Exa API schema (fixed, page-level) | Custom schemas per fragment type (11 types) |
| **Collection** | Common Crawl full pages → filter for quality | Extract fragments from pages OR targeted scraping |
| **Quality Filter** | Optimize for clean, well-formed HTML | Include messy, malformed HTML as features |
| **Negative Examples** | Excluded (filtered out SPAs, errors) | Included as training data (3 negative types) |
| **Token Range** | 4,000 - 128,000 | 200 - 8,000 |
| **Augmentation Focus** | Structural variations of full pages | Fragment extraction with varying noise levels |
| **Training Task** | Page → JSON conversion | Fragment identification + extraction in noisy context |
| **Validation Data** | Augmented pages | Real, unaugmented fragments only |

**Bottom Line**: The original plan optimized for page quality. The revised plan optimizes for extraction robustness in messy, real-world HTML.

---

## Appendix B: Risk Mitigation

### Risk 1: Insufficient Seed Examples
**Mitigation**:
- Reuse existing 469 crawled pages for fragment extraction
- Supplement with targeted scraping of high-quality sites
- Minimum viable: 50 seeds (Phase 1), expandable to 100+ (Phase 2)

### Risk 2: Augmentation Doesn't Improve Performance
**Mitigation**:
- Pilot testing in Week 3 (500 examples)
- Ablation studies per augmentation technique
- Only scale techniques that show validation improvement
- Fallback: Use real seeds only if augmentation hurts

### Risk 3: Schema Too Complex for Small Model
**Mitigation**:
- Start with 3-4 fragment types in pilot
- Measure per-type performance
- Prune types or simplify schemas if model struggles
- Multi-stage approach: Type classifier → Type-specific extractor

### Risk 4: Manual Annotation Bottleneck
**Mitigation**:
- Build annotation UI (HTML viewer + JSON editor with schema validation)
- Use Claude/GPT-4 for initial JSON drafts (human review required)
- Parallelize: Annotate 10-15 seeds in Week 1, rest in Week 2
- Accept 50 seeds minimum for pilot validation

### Risk 5: Data Leakage in Train/Val/Test Split
**Mitigation**:
- Split seed examples BEFORE augmentation
- Track seed IDs in augmented examples
- Validation script: Ensure no val/test seed appears in training data
- Automated check in dataset validation pipeline

---

## Appendix C: Tools and Scripts

### Required Tooling

**1. Seed Annotation UI** (`tools/annotate_seeds.py`)
- Load HTML snippet, display in viewer
- JSON editor with schema validation
- Save HTML + JSON as seed pair
- Track annotation progress

**2. Fragment Extractor** (`tools/extract_fragments.py`)
- Parse HTML pages
- Identify candidate fragments (heuristic-based)
- Extract with configurable noise radius
- Manual review and selection

**3. Augmentation Engine** (`scripts/augment_seeds.py`)
- Load seed examples
- Apply augmentation techniques (Tier 1, 2, 3)
- Validate each variation
- Output JSONL training files

**4. Validation Suite** (`scripts/validate_dataset.py`)
- Schema compliance checks
- HTML parseability tests
- Token distribution analysis
- Deduplication detection
- Quality metric computation

**5. Chat Format Converter** (`scripts/convert_to_chat.py`)
- Convert JSONL to chat format
- Generate system prompts
- Validate message structure

**6. Dataset Statistics Generator** (`scripts/generate_stats.py`)
- Fragment type distribution
- Token count histograms
- Augmentation technique coverage
- Noise level analysis
- Export to markdown report

### Development Stack

- **Python 3.13** with `uv` for dependency management
- **BeautifulSoup4** for HTML parsing
- **Pydantic** for schema validation
- **tiktoken** for token counting
- **datasets** (HuggingFace) for dataset management
- **tqdm** for progress tracking
- **pytest** for testing validation logic

---

## Appendix D: Fragment Collection Heuristics

### Product Card Detection
```python
def is_product_fragment(element):
    has_price = bool(element.find(class_=re.compile(r'price|cost|amount')))
    has_title = bool(element.find(['h1', 'h2', 'h3', 'h4']))
    has_description = bool(element.find(class_=re.compile(r'desc|summary|details')))
    has_image = bool(element.find('img'))

    return sum([has_price, has_title, has_description, has_image]) >= 3
```

### Event Listing Detection
```python
def is_event_fragment(element):
    has_datetime = bool(element.find('time') or element.find(datetime=True))
    has_location = bool(element.find(class_=re.compile(r'location|venue|address')))
    has_title = bool(element.find(['h1', 'h2', 'h3', 'h4']))

    return sum([has_datetime, has_location, has_title]) >= 2
```

### Contact/Person Card Detection
```python
def is_person_fragment(element):
    has_email = bool(element.find('a', href=re.compile(r'^mailto:')))
    has_phone = bool(element.find('a', href=re.compile(r'^tel:')))
    has_name = bool(element.find(class_=re.compile(r'name|author|person')))
    has_image = bool(element.find('img'))

    return sum([has_email, has_phone, has_name, has_image]) >= 2
```

### Pricing Table Detection
```python
def is_pricing_fragment(element):
    price_elements = element.find_all(class_=re.compile(r'price|plan|tier'))
    has_multiple_plans = len(price_elements) >= 2
    has_features = bool(element.find(['ul', 'ol']))

    return has_multiple_plans and has_features
```

Similar heuristics for recipes, jobs, reviews, articles, and negative examples.

---

**End of Revised Phase 1 Plan**

This plan prioritizes extraction robustness over page quality, schema-driven data collection over exploratory crawling, and iterative validation over large-scale generation. The goal is a dataset that teaches a small model to find signal in noise, not just convert clean HTML to JSON.
