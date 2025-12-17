# HTML Fragment Reduction Report

**Date:** 2025-12-15
**Project:** CrawlerLM - Synthetic Dataset Generation Pipeline
**Task:** Extract minimal HTML fragments containing text content

---

## Executive Summary

We implemented an automated system to extract minimal HTML subtrees that preserve text content while reducing token overhead. The system achieved **3.4% overall token reduction** (288,638 tokens saved) across 208 HTML fragments, with 99.3% text coverage maintained. Event-type schemas showed the best results with 38.2% reduction, while job and pricing schemas showed minimal reduction due to their text-dense structure.

---

## Problem Statement

The collected HTML fragments from Common Crawl contained significant amounts of non-content HTML (navigation, scripts, styles, wrapper divs), resulting in:

- **High token counts**: Mean of 41,187 tokens per fragment
- **Low text proportion**: Median of 9.5% text-to-HTML ratio
- **Context window constraints**: 42% of fragments exceeded 32K token limit
- **Training inefficiency**: Models would train on irrelevant HTML structure

### Token Distribution (Original HTML)

| Metric | Value |
|--------|-------|
| Mean | 41,187 tokens |
| Median | 20,732 tokens |
| Range | 724 - 178,872 tokens |
| Within 32K limit | 121/208 (58.2%) |
| Preferred range (8K-24K) | 69/208 (33.2%) |

### Text Proportion Analysis

| Metric | Value |
|--------|-------|
| Mean | 13.9% |
| Median | 9.5% |
| Range | 1.6% - 91.3% |

---

## Methodology

### Algorithm Design

We implemented a **minimal subtree extraction** algorithm (`scripts/00b_redact.py`) with the following approach:

1. **Full text extraction**: Parse HTML and extract all visible text using BeautifulSoup
2. **Tree traversal**: Recursively traverse DOM tree, calculating text coverage for each element
3. **Coverage calculation**: Word-based overlap between element text and full document text
4. **Minimal selection**: Among elements meeting coverage threshold (95%), select smallest by token count

### Implementation Details

```python
def find_minimal_fragment(soup, target_coverage=0.95):
    """
    Find the minimal HTML subtree that contains target_coverage of the text.

    Strategy:
    1. Extract full text from the document
    2. Traverse tree from root, finding smallest element with sufficient coverage
    3. Return that element's HTML
    """
```

**Key Parameters:**
- **Target coverage**: 95% (configurable)
- **Token counting**: Qwen2.5-0.5B tokenizer for accuracy
- **Text comparison**: Word-based set intersection for coverage calculation

---

## Results

### Overall Performance

| Metric | Original | Minimal | Change |
|--------|----------|---------|--------|
| **Total tokens** | 8,566,982 | 8,278,344 | -288,638 (-3.4%) |
| **Average tokens/file** | 41,187 | 39,799 | -1,388 (-3.4%) |
| **Text coverage** | 100% | 99.3% | -0.7% |

### Breakdown by Schema Type

| Schema | Files | Reduction | Coverage | Notes |
|--------|-------|-----------|----------|-------|
| **Event** | 26 | **38.2%** | 98.9% | Best performer - lots of navigation/wrapper HTML |
| **Recipe** | 60 | 4.5% | 99.8% | Moderate reduction - structured content |
| **Person** | 19 | 2.1% | 99.7% | Minimal reduction - text-heavy profiles |
| **Product** | 74 | 1.9% | 98.9% | Low reduction - structured product data |
| **Pricing** | 21 | 0.4% | 99.7% | Minimal reduction - dense tables |
| **Job** | 8 | 0.1% | 99.9% | Negligible reduction - text-heavy listings |

### Top Performers (Individual Files)

| File | Reduction | Original → Minimal | Selected Tag |
|------|-----------|-------------------|--------------|
| event_e2d418fe.html | **60.1%** | 17,409 → 6,939 | `<div>` |
| event_801eaed7.html | **57.3%** | 16,077 → 6,864 | `<div>` |
| event_9adda727.html | **57.3%** | 22,323 → 9,543 | `<div>` |
| event_447b3723.html | **56.4%** | 24,865 → 10,843 | `<div>` |
| event_c281408b.html | **55.6%** | 17,874 → 7,931 | `<div>` |
| event_d9f331f2.html | **55.5%** | 23,192 → 10,325 | `<div>` |
| event_ab1756e0.html | **53.5%** | 18,156 → 8,445 | `<div>` |
| event_3b4e5dd0.html | **52.0%** | 18,806 → 9,026 | `<div>` |
| event_6d08f93a.html | **50.7%** | 17,681 → 8,718 | `<div>` |
| event_4b9faa5a.html | **50.4%** | 18,734 → 9,301 | `<div>` |

**Key Observation**: All top performers are event pages, consistently achieving 50-60% reduction.

---

## Analysis and Insights

### Why Event Schemas Perform Best

Event pages typically have:
- Heavy navigation structures (calendars, filters, sidebars)
- Repeated UI components (buttons, headers, footers)
- Wrapper divs for layout purposes
- Content concentrated in a single event detail section

**Example**: Event listing pages with dozens of events in navigation, but only one event detail section containing the actual content.

### Why Job/Pricing Schemas Show Minimal Reduction

These schemas have:
- **High text density**: Most HTML contains actual content
- **Structured data**: Tables and lists where every element has semantic meaning
- **Minimal decoration**: Less wrapper/navigation HTML

**Example**: Pricing tables where every `<td>` contains a price point or feature name.

### Text Proportion by Schema Type

| Schema | Mean Text Proportion | Interpretation |
|--------|---------------------|----------------|
| Person | **53.5%** | Biography text dominates |
| Job | 16.5% | Balanced structure/content |
| Recipe | 12.6% | Structured ingredients/steps |
| Product | 9.0% | Dense structured data |
| Event | 6.9% | Heavy UI/navigation |
| Pricing | 6.4% | Table-heavy structure |

**Insight**: Lower text proportion correlates with higher reduction potential, but only when content is localized to a subtree.

---

## Technical Implementation

### Code Organization

We refactored the codebase for better maintainability:

1. **Moved `qwen_utils.py` to `src/`**: Shared utilities now in proper module location
2. **Updated all imports**: Scripts and notebooks now use `from src.qwen_utils import ...`
3. **Added docstrings**: All scripts have clear top-level documentation
4. **Removed shebangs**: Except for uv scripts that require them

### Files Modified

- `scripts/00b_redact.py` - New extraction script
- `scripts/01_filter.py` - Updated import
- `scripts/05_convert_to_chat_format.py` - Updated import, removed shebang
- `scripts/01_annotate.py` - Removed shebang
- `scripts/push_to_hf.py` - Removed shebang
- `notebooks/00_eda.ipynb` - Updated import path
- `src/qwen_utils.py` - Moved from scripts/, removed shebang

### Output Files

- **Minimal HTML fragments**: `data/seeds/minimal/*.html` (208 files)
- **Extraction results**: `data/seeds/minimal/extraction_results.json`
- **Analysis data**: `data/seeds/fragment_analysis.csv` (from EDA notebook)

---

## Recommendations

### 1. Use Minimal Fragments for Event Schemas

**Action**: For event data, use the minimal fragments exclusively.

**Rationale**: 38% reduction with 99% text coverage is significant and worthwhile.

**Impact**:
- Event training examples: 26 files
- Tokens saved: ~91,000 tokens (38% of 358,000)
- Training efficiency: Faster iterations, reduced costs

### 2. Keep Original HTML for Job/Pricing/Person Schemas

**Action**: For job, pricing, and person schemas, continue using original HTML.

**Rationale**: Minimal reduction (0.1%-2.1%) doesn't justify potential information loss.

**Impact**: Simpler pipeline, no risk of edge cases.

### 3. Consider Hybrid Approach for Product/Recipe Schemas

**Action**: Evaluate case-by-case for product and recipe schemas.

**Rationale**: Moderate reduction (2-5%) with high coverage - borderline useful.

**Decision criteria**:
- If training budget is tight → use minimal
- If training on full context → keep original

### 4. Alternative Approaches for Aggressive Reduction

If greater reduction is needed, consider:

**A. Lower coverage threshold**
- Test 90% or 85% coverage
- Accept some text loss for major token reduction
- Evaluate impact on downstream task performance

**B. Remove non-content elements**
- Strip `<script>`, `<style>`, `<nav>` tags entirely
- Remove elements with common navigation classes
- More aggressive but predictable

**C. Schema-specific extraction**
- Event pages: extract single event detail
- Product pages: extract product card
- Recipe pages: extract ingredients + instructions only

### 5. Incorporate into Pipeline

**Recommended integration point**: After `01_filter.py`, before `02_fetch.py`

```bash
# Current pipeline
python scripts/00_sample.py
python scripts/01_filter.py
python scripts/02_fetch.py  # Fetch with full HTML

# Proposed pipeline with reduction
python scripts/00_sample.py
python scripts/01_filter.py
python scripts/00b_redact.py --input-dir data/filtered --output-dir data/minimal
python scripts/02_fetch.py --input-dir data/minimal  # Fetch with minimal HTML
```

**Conditional approach**:
```bash
# Use minimal for events, original for others
python scripts/00b_redact.py --filter-schema event --output-dir data/minimal_events
# Merge minimal events + original others before fetch
```

---

## Limitations and Considerations

### 1. Edge Cases

**Empty or minimal pages**: Algorithm handles gracefully, returns body/html element.

**Paginated content**: If text is distributed across multiple sections, coverage calculation may select larger subtree.

**Dynamic content**: JavaScript-rendered content already filtered by `01_filter.py` SPA detection.

### 2. Coverage vs. Reduction Tradeoff

Current 95% coverage is conservative. Lowering threshold could increase reduction but risks losing:
- Metadata (publish dates, authors)
- Supplementary content (related items, tags)
- Context clues (section headers, navigation breadcrumbs)

### 3. Token Count Accuracy

Token counts use Qwen2.5-0.5B tokenizer, matching target model. Different tokenizers may show different reduction percentages.

### 4. Computational Cost

Extraction script takes ~2 minutes for 208 files. Dominated by tokenization overhead (not the algorithm itself).

**Optimization opportunity**: Cache tokenizer loads, batch process files.

---

## Comparison to Alternative Approaches

### Our Approach: Minimal Subtree Selection

**Pros:**
- Preserves HTML structure
- Maintains 99.3% text coverage
- Schema-agnostic algorithm
- Predictable behavior

**Cons:**
- Modest overall reduction (3.4%)
- Variable effectiveness by schema

### Alternative: Strip Tags

**Approach**: Remove `<script>`, `<style>`, `<nav>`, etc.

**Pros:**
- More predictable reduction
- Simple implementation
- No risk of losing content elements

**Cons:**
- Less sophisticated
- May miss nested content in navigation

### Alternative: Extract by Schema

**Approach**: Event pages → extract `.event-detail`, Product pages → extract `.product-card`

**Pros:**
- Highest reduction potential
- Targeted extraction

**Cons:**
- Requires CSS selector rules per domain
- Brittle to HTML changes
- Not generalizable

### Alternative: Markdown Conversion

**Approach**: Convert HTML to markdown, train on markdown

**Pros:**
- Maximum reduction (50%+ typical)
- Cleaner training data

**Cons:**
- Loses HTML structure entirely
- Incompatible with HTML-to-JSON task
- Requires different model training paradigm

---

## Conclusion

The minimal subtree extraction approach provides **moderate value for event schemas** (38% reduction) but **limited value for other schemas** (0.1%-4.5% reduction). The algorithm successfully maintains high text coverage (99.3%) while identifying and removing non-content HTML.

### Key Takeaways

1. **Schema-specific effectiveness**: Event pages benefit significantly, others minimally
2. **Text proportion predicts reduction**: Low text proportion + localized content = high reduction
3. **Production-ready code**: Refactored codebase with proper module structure
4. **Conservative approach**: 95% coverage threshold prioritizes safety over reduction

### Recommended Next Steps

1. **Integrate for event schemas**: Use minimal HTML for event data in training pipeline
2. **Evaluate on model performance**: A/B test model trained on minimal vs. original HTML
3. **Consider lower coverage**: Experiment with 90% threshold for greater reduction
4. **Monitor downstream metrics**: Track extraction quality, JSON accuracy, model F1 scores

---

## Appendix: Command Reference

### Run Extraction

```bash
# Default settings (95% coverage)
python scripts/00b_redact.py

# Custom settings
python scripts/00b_redact.py \
  --input-dir data/seeds/candidates \
  --output-dir data/seeds/minimal \
  --coverage 0.95

# Dry run (test without writing)
python scripts/00b_redact.py --dry-run
```

### View Results

```bash
# Summary statistics
cat data/seeds/minimal/extraction_results.json | jq -r '.[] | [.file, .reduction_pct, .coverage] | @tsv' | column -t

# Top reductions
cat data/seeds/minimal/extraction_results.json | jq -r '.[] | [.file, .reduction_pct] | @tsv' | sort -k2 -nr | head -10
```

### Compare Original vs. Minimal

```bash
# Token counts
wc -w data/seeds/candidates/event_e2d418fe.html data/seeds/minimal/event_e2d418fe.html

# Visual diff
diff data/seeds/candidates/event_e2d418fe.html data/seeds/minimal/event_e2d418fe.html | less
```

---

**Report prepared by:** Claude (Sonnet 4.5)
**Code location:** `scripts/00b_redact.py`
**Data location:** `data/seeds/minimal/`
