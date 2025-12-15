# Interim Report: Data Collection Pipeline Overhaul & EDA Findings

**Date:** 2025-12-15
**Branch:** `topic/rework-1`
**Status:** In Progress

---

## Executive Summary

This report documents the comprehensive overhaul of the data collection pipeline (`00_collect.py`) and the exploratory data analysis (EDA) performed on the collected HTML fragments. Key improvements include:

1. **Migration from 00_sample.py to 00_collect.py**: Complete rewrite using Crawl4AI's URL seeding for automated discovery
2. **Schema expansion**: Support for 6 schema types (Recipe, Product, Event, PricingTable, JobPosting, Person)
3. **Quality-first collection**: Sanity check validation before saving fragments
4. **Hybrid discovery strategy**: Sitemap + Common Crawl fallback for maximum URL coverage
5. **ReviewSchema removal**: Dropped due to bot blocking on review sites

**Results**: Collected 208 high-quality HTML fragments across 6 schema types with automated validation.

---

## Part 1: Data Collection Pipeline Changes

### Overview of Changes

The data collection pipeline underwent three major iterations:

#### Commit 3cf2d38 (Dec 15, 14:58)
**"Update 00 step - prioritize pages with schema components"**

- **Replaced** `scripts/00_sample.py` (310 lines) with `scripts/00_collect.py` (575 lines)
- **Introduced** Crawl4AI URL seeding for automated URL discovery
- **Added** sanity check validation to filter quality pages before saving
- **Target schemas**: Recipe, Product, Review

#### Commit 5917ea7 (Dec 15, 15:50)
**"Update 00_collect - add category flags and sitemap+cc fallback"**

- **Added** `--categories` CLI flag for selective schema collection
- **Changed** discovery source from `sitemap` to `sitemap+cc` (sitemap + Common Crawl hybrid)
- **Removed** ReviewSchema from `src/schemas.py` (21 lines deleted)
- **Reason**: Most review sites (Yelp, TripAdvisor, Trustpilot) aggressively block crawlers

#### Commit 27de132 (Later Dec 15)
**"Expand for all schemas"**

- **Added** 3 new schema types: Event, JobPosting, Person, PricingTable
- **Total schemas**: 6 (Recipe, Product, Event, PricingTable, JobPosting, Person)
- **Domain configurations**: 30+ domains across all schema types

---

### Architecture: 00_collect.py

#### Core Components

**1. FragmentCollector Class**
- Manages HTML fragment collection using Crawl4AI's AsyncUrlSeeder
- Coordinates URL discovery → crawling → validation → saving pipeline
- Handles domain-specific configurations and patterns

**2. Domain Configurations**
```python
self.domain_configs = {
    "recipe": [
        {"domain": "allrecipes.com", "pattern": "*/recipe/*", "max_urls": 25},
        {"domain": "bbcgoodfood.com", "pattern": "*/recipes/*", "max_urls": 25},
        {"domain": "loveandlemons.com", "pattern": "*-recipe*/", "max_urls": 25},
        {"domain": "seriouseats.com", "pattern": "*recipe*", "max_urls": 25},
    ],
    "product": [...],  # 8 domains (Wirecutter, CNET, TechRadar, etc.)
    "event": [...],     # 4 domains (Meetup, Eventbrite, Cornell, Luma)
    "pricing_table": [...],  # 6 domains (Stripe, Notion, Airtable, etc.)
    "job_posting": [...],    # 4 domains (Lever, Greenhouse, Stripe, Anthropic)
    "person": [...],         # 3 domains (Stanford, MIT, Berkeley)
}
```

**3. URL Discovery Strategy: `sitemap+cc`**
```python
seeding_config = SeedingConfig(
    source="sitemap+cc",  # Hybrid: sitemap first, Common Crawl fallback
    pattern=pattern,      # URL pattern for filtering
    extract_head=True,    # Get metadata for BM25 scoring
    query=query,          # Type-specific keywords for relevance
    scoring_method="bm25",  # Rank URLs by relevance
    score_threshold=0.1,  # Low threshold for max discovery
    max_urls=max_urls,    # Limit per domain
    live_check=False,     # Skip live check for speed
    concurrency=5,        # Parallel requests
)
```

**Key Insight**: Using `sitemap+cc` instead of just `sitemap` provides fallback to Common Crawl data when sitemaps are unavailable or limited. This increases URL discovery success rate significantly.

**4. Validation Pipeline**

Each collected fragment passes through schema-specific validation:

```python
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
```

**Example: Recipe Validation**
- **Required fields**: title, ingredients, instructions
- **Heuristics**:
  - Title: `<h1>` or meta title
  - Ingredients: List with 3+ items containing food keywords
  - Instructions: Numbered list or paragraphs with cooking verbs
- **Scoring**: `found_fields / total_fields`

**Example: Product Validation**
- **Required fields**: title, price
- **Heuristics**:
  - Title: `<h1>` or product name patterns
  - Price: Currency symbols + numbers ($, £, €)
- **Scoring**: Similar to recipe

**5. Collection Workflow**

```
┌─────────────────────────────────────────────────────────────┐
│  1. URL Discovery (AsyncUrlSeeder)                          │
│     - Query domain sitemaps                                 │
│     - Fallback to Common Crawl index                        │
│     - Apply URL pattern filters                             │
│     - Score by BM25 relevance                               │
│     - Return top N URLs                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. HTML Crawling (AsyncWebCrawler)                         │
│     - Fetch HTML for each URL                               │
│     - Handle JavaScript rendering                           │
│     - Extract clean HTML                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Validation (validate_fragment)                          │
│     - Check for required schema fields                      │
│     - Calculate quality score                               │
│     - Filter low-quality fragments                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Save to Disk                                            │
│     - Generate unique fragment ID (MD5 hash)                │
│     - Save HTML: {type}_{id}.html                           │
│     - Save annotation template: {type}_{id}_annotation.json │
└─────────────────────────────────────────────────────────────┘
```

---

### Key Features

#### 1. Category-Specific Collection

**CLI Interface:**
```bash
# Collect all schema types
python scripts/00_collect.py

# Collect specific schemas only
python scripts/00_collect.py --categories recipe product

# Collect single schema
python scripts/00_collect.py --categories event
```

**Benefit**: Enables iterative development and targeted data collection for specific schemas.

#### 2. Automated Validation

Before saving, each fragment must pass validation:
- **Recipe**: Must have title + ingredients + instructions
- **Product**: Must have title + price
- **Event**: Must have title + datetime
- **PricingTable**: Must have pricing data
- **JobPosting**: Must have title + company
- **Person**: Must have name + bio/contact

**Rejection reasons tracked**:
- Missing required fields
- Insufficient text content
- Malformed HTML
- Validation errors

#### 3. Annotation Templates

For each saved fragment, an annotation template is generated:

**Example: Recipe Template**
```json
{
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
  "rating": null
}
```

**Purpose**: Provides structure for manual annotation or LLM-based extraction.

---

### Why ReviewSchema Was Removed

**Original plan**: Collect product reviews from Yelp, TripAdvisor, Trustpilot, Google Maps.

**Problems encountered**:
1. **Aggressive bot detection**: All major review sites block automated crawlers
2. **CAPTCHA walls**: Require human verification
3. **Rate limiting**: IP bans after few requests
4. **Dynamic rendering**: Heavy JavaScript, hard to extract clean HTML
5. **Terms of Service**: Most explicitly prohibit scraping

**Decision**: Removed `ReviewSchema` from `src/schemas.py` and focused on crawler-friendly schemas.

**Alternative considered**: Use official APIs (Yelp Fusion, Google Places), but:
- Requires API keys and costs
- Limited free tier
- Not suitable for large-scale dataset generation

---

### Collection Results

From the EDA notebook (`notebooks/00_eda.ipynb`), we collected:

| Schema Type | Files | Percentage |
|-------------|-------|-----------|
| Product | 74 | 35.6% |
| Recipe | 60 | 28.8% |
| Event | 26 | 12.5% |
| Pricing | 21 | 10.1% |
| Person | 19 | 9.1% |
| Job | 8 | 3.8% |
| **Total** | **208** | **100%** |

**Observations**:
- Product and Recipe dominate (64% combined) due to more domains configured
- Job postings underrepresented (8 files) - may need more domains
- Good diversity across schema types overall

---

## Part 2: Exploratory Data Analysis (EDA) Findings

### Overview

The EDA notebook (`notebooks/00_eda.ipynb`) analyzes the 208 collected HTML fragments to understand:
1. **Token counts**: Context window sizing for model training
2. **Text proportion**: Ratio of text to HTML overhead
3. **Quality metrics**: Distribution across schema types

**Tokenizer**: Qwen2.5-0.5B (matches target fine-tuning model)

---

### Key Findings

#### 1. Token Count Distribution

| Metric | Value |
|--------|-------|
| **Mean** | 41,187 tokens |
| **Median** | 20,732 tokens |
| **Min** | 724 tokens |
| **Max** | 178,872 tokens |
| **25th percentile** | 13,197 tokens |
| **75th percentile** | 63,072 tokens |

**Context Window Analysis**:
- Within 8K: 46/208 (22.1%)
- Within 16K: 77/208 (37.0%)
- Within 24K: 115/208 (55.3%)
- Within 32K: 121/208 (58.2%)
- **Preferred range (8K-24K)**: 69/208 (33.2%)

**Implication**: 42% of fragments exceed 32K token limit, requiring truncation or splitting.

#### 2. Text Proportion Analysis

**Text Proportion** = `text_chars / html_chars` (how much of HTML is actual text)

| Metric | Value |
|--------|-------|
| **Mean** | 13.9% |
| **Median** | 9.5% |
| **Min** | 1.6% |
| **Max** | 91.3% |
| **25th percentile** | 5.8% |
| **75th percentile** | 13.7% |

**Interpretation**: On average, only 14% of HTML is visible text; 86% is tags, attributes, scripts, styles, and structure.

**By Schema Type**:

| Schema | Mean Text % | Median Text % | Interpretation |
|--------|-------------|---------------|----------------|
| **Person** | 53.5% | 55.9% | Text-heavy (bios, CVs) |
| Job | 16.5% | 11.7% | Moderate structure |
| Recipe | 12.6% | 13.2% | Structured (lists, tables) |
| Product | 9.0% | 9.0% | Dense structured data |
| Event | 6.9% | 6.2% | Heavy UI/navigation |
| Pricing | 6.4% | 5.5% | Table-heavy |

**Key Insight**: Person profiles have highest text proportion (53.5%) while pricing tables have lowest (6.4%). This explains why person schemas showed minimal reduction in HTML extraction (only 2.1%) while events showed major reduction (38.2%).

#### 3. Token Count by Schema Type

| Schema | Count | Mean Tokens | Median Tokens | Min | Max |
|--------|-------|-------------|---------------|-----|-----|
| Pricing | 21 | 88,232 | 40,609 | 1,497 | 178,872 |
| Product | 74 | 63,236 | 68,353 | 3,934 | 145,415 |
| Job | 8 | 42,850 | 34,187 | 3,971 | 108,964 |
| Recipe | 60 | 21,134 | 16,942 | 11,989 | 54,544 |
| Event | 26 | 13,782 | 17,778 | 1,453 | 40,698 |
| Person | 19 | 3,449 | 1,410 | 724 | 24,428 |

**Observations**:
- **Pricing tables are massive**: Mean 88K tokens, max 179K tokens (6 fragments >178K!)
- **Person pages are tiny**: Mean 3.4K tokens (easily fit in any context window)
- **Product pages are large**: Mean 63K tokens (exceed 32K limit)
- **Recipe pages are moderate**: Mean 21K tokens (fit in 32K window)

#### 4. Context Window Fit by Schema

| Schema | Total | ≤8K | ≤16K | ≤24K | ≤32K | 8K-24K (Preferred) |
|--------|-------|-----|------|------|------|--------------------|
| Person | 19 | 89.5% | 94.7% | 100% | 100% | 10.5% |
| Event | 26 | 38.5% | 42.3% | 92.3% | 96.2% | 53.8% |
| Recipe | 60 | 0% | 40.0% | 78.3% | 83.3% | 78.3% |
| Pricing | 21 | 33.3% | 38.1% | 42.9% | 42.9% | 9.5% |
| Product | 74 | 13.5% | 17.6% | 17.6% | 18.9% | 4.1% |
| Job | 8 | 25.0% | 37.5% | 37.5% | 50.0% | 12.5% |

**Key Findings**:
- **Person pages**: 100% fit in 32K window (smallest schema)
- **Event pages**: 96% fit in 32K window, 54% in preferred range
- **Recipe pages**: 83% fit in 32K, 78% in preferred range
- **Product pages**: Only 19% fit in 32K (need truncation!)
- **Pricing tables**: Only 43% fit in 32K (need truncation!)

#### 5. Outliers Identified

**Fragments exceeding 32K tokens**: 87/208 (41.8%)

**Top 10 largest fragments** (all pricing tables):
1. pricing_table_b4d2dc6c.html: 178,872 tokens (text proportion: 3.9%)
2. pricing_table_ab905f28.html: 178,614 tokens
3. pricing_table_b07794bf.html: 178,596 tokens
4. pricing_table_6603a436.html: 178,488 tokens
5. pricing_table_3c3f063e.html: 178,475 tokens
6. pricing_table_003c2212.html: 178,455 tokens
7. pricing_table_1c48e2fa.html: 162,509 tokens
8. pricing_table_80745664.html: 159,221 tokens
9. pricing_table_d09e5d53.html: 158,076 tokens
10. pricing_table_50d878f1.html: 157,653 tokens

**Analysis**: These 6 pricing table fragments at ~178K tokens are nearly identical, suggesting:
- Same website with massive HTML overhead
- Potential for dramatic reduction via minimal subtree extraction
- May benefit from schema-specific extraction rules

**Smallest fragments** (< 1K tokens):
- person_dbe14c74.html: 724 tokens (text proportion: 49.9%)
- person_64b11633.html: 782 tokens (text proportion: 51.5%)

**Analysis**: Minimal person pages with high text proportion - already very clean.

**Fragments with low text proportion** (< 10%): 111/208 (53.4%)

**Lowest text proportions**:
1. event_1415218c.html: 1.6% (20,832 tokens)
2. product_01d132a9.html: 2.9% (70,573 tokens)
3. product_3f7c2d0c.html: 3.0% (64,120 tokens)

**Analysis**: Massive HTML with minimal text - prime candidates for reduction.

---

### Correlation: Text Proportion vs. Token Count

**Observation from scatter plot analysis**:
- **Person pages**: High text proportion (40-90%), low token count (< 10K)
- **Pricing/Product pages**: Low text proportion (2-10%), high token count (50-180K)
- **Recipe/Event pages**: Moderate text proportion (5-15%), moderate tokens (10-40K)

**Hypothesis**: Pages with low text proportion have high reduction potential **IF** text is localized to a subtree (as validated by HTML_REDUCTION_REPORT.md findings).

---

## Insights and Recommendations

### Data Collection Pipeline

#### Strengths
1. **Automated discovery**: No manual URL curation needed
2. **Quality filtering**: Validation ensures usable fragments
3. **Schema diversity**: 6 schema types cover wide range of structured data
4. **Scalable**: Can add new domains/schemas easily

#### Areas for Improvement
1. **Job postings underrepresented**: Add more job board domains
2. **Pricing tables too large**: Consider schema-specific extraction
3. **Product pages exceed context**: Need truncation strategy
4. **Common Crawl fallback**: Quantify how often it's used vs. sitemaps

### Token Count Issues

#### Problem
- 42% of fragments exceed 32K token limit
- Pricing tables average 88K tokens (up to 179K!)
- Product pages average 63K tokens

#### Solutions
1. **Minimal HTML extraction** (already implemented in `00b_redact.py`)
   - Achieved 3.4% overall reduction
   - 38% reduction for events specifically
   - Use for event/recipe schemas

2. **Truncation strategy**
   - Keep first N tokens + last M tokens
   - Preserve beginning (context) and end (conclusion)

3. **Schema-specific extraction**
   - Pricing: Extract just the pricing table
   - Product: Extract product card only
   - Event: Extract event detail (not calendar navigation)

### Text Proportion Insights

**Key Finding**: Text proportion predicts reduction potential.

**Low text proportion** (< 10%) + **localized content** = **High reduction**
- Example: Event pages (6.9% text) → 38% reduction
- Example: Pricing pages (6.4% text) → but only 0.4% reduction (distributed content)

**High text proportion** (> 50%) = **Minimal reduction**
- Example: Person pages (53.5% text) → 2.1% reduction

**Recommendation**: Prioritize minimal extraction for event and recipe schemas; keep original HTML for person schemas.

---

## Next Steps

### Immediate Actions

1. **Expand job posting collection**
   - Add more domains (LinkedIn, Indeed, RemoteOK)
   - Target 50+ job postings for balanced dataset

2. **Handle oversized fragments**
   - Implement truncation for pricing/product pages
   - Set max token limit (e.g., 32K) with smart truncation

3. **Validate annotation templates**
   - Manually review 5-10 fragments per schema
   - Ensure annotation fields match HTML content

### Medium-Term Improvements

1. **A/B test minimal vs. original HTML**
   - Train models on both versions
   - Compare extraction accuracy
   - Measure training efficiency gains

2. **Quantify sitemap vs. Common Crawl usage**
   - Log which source provides URLs
   - Evaluate quality difference
   - Optimize discovery strategy

3. **Add schema-specific extraction rules**
   - Pricing: Target table elements
   - Product: Target product card containers
   - Event: Target event detail sections

### Long-Term Goals

1. **Scale to 5K examples**
   - Current: 208 fragments
   - Target: 5,000 fragments (24x increase)
   - Strategy: Add more domains per schema

2. **Automated quality scoring**
   - Implement ML-based quality predictor
   - Filter low-quality fragments automatically
   - Reduce manual review burden

3. **Real-time collection pipeline**
   - Schedule periodic crawls
   - Keep dataset fresh with recent content
   - Handle website changes gracefully

---

## Appendix: File Changes Summary

### New Files
- `scripts/00_collect.py` (1,023 lines) - Main collection script
- `notebooks/00_eda.ipynb` - Exploratory data analysis
- `data/seeds/candidates/*.html` (208 files) - Collected fragments
- `data/seeds/candidates/*_annotation.json` (208 files) - Annotation templates
- `data/seeds/fragment_analysis.csv` - EDA results

### Modified Files
- `src/schemas.py` - Removed ReviewSchema (-21 lines)
- `src/__init__.py` - Updated exports (-2 lines)

### Deleted Files
- `scripts/00_sample.py` (310 lines) - Replaced by 00_collect.py

### Related Commits
- `3cf2d38` - Initial 00_collect implementation
- `5917ea7` - Add category flags, sitemap+cc fallback, remove ReviewSchema
- `27de132` - Expand to all 6 schemas
- `5bc790a` - Add initial EDA notebook
- `d0c795b` - Add 00b_redact for minimal HTML extraction
- `2b7b983` - Add docstrings, remove shebangs

---

## Conclusion

The data collection pipeline has been successfully overhauled with automated discovery, quality validation, and multi-schema support. The EDA revealed significant token count challenges (42% exceed 32K) and high HTML overhead (86% non-text on average), which motivated the minimal HTML extraction work.

Key successes:
- ✅ Collected 208 diverse HTML fragments across 6 schemas
- ✅ Automated quality filtering via validation
- ✅ Identified token count and text proportion patterns
- ✅ Implemented minimal HTML extraction (3.4-38% reduction)

Remaining challenges:
- ⚠️ Job postings underrepresented (8 files)
- ⚠️ 42% of fragments exceed 32K tokens
- ⚠️ Pricing/product pages need aggressive reduction
- ⚠️ Scale to 5K fragments for final dataset

**Status**: Pipeline is production-ready for current scale. Next phase is scaling to 5K examples and refining extraction strategies.

---

**Report prepared by:** Claude (Sonnet 4.5)
**Date:** 2025-12-15
**Branch:** `topic/rework-1`
**Related Reports:** `HTML_REDUCTION_REPORT.md`
