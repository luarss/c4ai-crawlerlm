# Plan for Task A: Synthetic Dataset Generation

## Overview
Sample diverse URLs from Common Crawl, extract real HTML examples, and generate synthetic variations to create 5k training examples for HTML → JSON conversion.

---

## 1. Set up project structure and dependencies

**Goal**: Establish development environment and directory structure

**Directory Structure**:
```
data/
  raw_html/
  processed/
  synthetic/
scripts/
schema/
```

---

## 2. Access Common Crawl index and sample diverse domain URLs

**Goal**: Query Common Crawl to get 50-100 URLs from diverse domains

**Strategy**:
- Query Common Crawl Index API (cdx-api) to get URL samples
- Implement domain diversity strategy:
  - Extract top-level domains (TLDs) to ensure variety (.com, .org, .edu, etc.)
  - Sample from different domain categories (news, e-commerce, blogs, documentation, etc.)
  - Use hash-based sampling to distribute across domain space
  - Target: 50-100 unique domains with 1-2 URLs each

**Metadata to Store**:
- Domain
- URL
- Crawl date
- Content type

---

## 3. Fetch HTML content from sampled URLs

**Goal**: Retrieve actual HTML content from Common Crawl WARC files

**Implementation**:
- Use Common Crawl WARC files to retrieve actual HTML content
- Fetching logic:
  - Download WARC segments containing target URLs
  - Extract HTML responses from WARC records
  - Handle errors and incomplete/malformed HTML gracefully

**Quality Filters**:
- Ensure HTML has sufficient content (not 404s, redirects)
- Prefer "messy" real-world HTML (various frameworks, inline styles, nested structures)
- Save raw HTML files with metadata

---

## 4. Exa JSON schema (already defined)

**Goal**: Use Exa's extraction format consistently across all examples

**Exa Schema** (fixed structure from Exa API):
```json
{
  "url": "string",
  "title": "string",
  "text": "string (full extracted text content in markdown format)",
  "author": "string or null",
  "published_date": "string or null",
  "image": "string (URL) or null",
  "favicon": "string (URL) or null",
  "id": "string (typically the URL)"
}
```

**Schema Characteristics**:
- Defined by Exa API - cannot be customized
- All fields are always present (null if not extracted)
- `text` field contains full semantic content in markdown
- Includes metadata like author and published_date when available
- Consistent format across all 50+ base examples

---

## 5. Create HTML → JSON extraction baseline (✅ COMPLETED)

**Goal**: Generate initial high-quality training examples

**Completed Pipeline**:
- ✅ 00_sample.py - Sampled ~400 diverse URLs from Common Crawl
- ✅ 01_filter.py - Selected best 50 URLs based on quality metrics
- ✅ 02_fetch.py - Extracted structured JSON using Exa API
- ✅ 03_join.py - Created golden.jsonl with matched HTML+JSON pairs

**Current Dataset** (`data/processed/golden.jsonl`):
- 50+ real-world HTML examples from diverse domains
- Each example includes raw HTML and Exa-extracted JSON
- Variety of frameworks (React, Vue, Nuxt, static HTML)
- Different content types (blogs, documentation, e-commerce, crypto)

**Output Format**:
```json
{"example_html": "<html>...</html>", "expected_json": {...}}
```

---

## 6. Generate synthetic variations programmatically

**Goal**: Scale from 50-100 base examples to 5000 total examples

**Augmentation Strategies**:
- **Structural variations**: Add/remove wrapper divs, change nesting depth
- **Attribute noise**: Add random classes, IDs, data attributes
- **Content perturbations**: Replace text with Faker-generated content
- **Style injection**: Add inline styles, empty elements, comments
- **HTML corruption**: Missing closing tags, malformed attributes, CDATA sections
- **Template variations**: Swap element types (div ↔ section, span ↔ em)

**Scaling Target**:
- Each base example should generate 50-100 variations
- Maintain consistent JSON output for each variation group

---

## 7. Scale to 5k examples with quality validation

**Goal**: Generate and validate complete dataset

**Generation**:
- 50 base examples × 100 variations = 5000 examples
- Ensure balanced distribution across HTML complexity levels

**Validation Pipeline**:
- Verify all JSONs match Exa schema (8 required fields)
- Check HTML parsability (can be parsed by standard parsers)
- Ensure `expected_json` remains unchanged across variations
- Manual spot-check random samples
- Calculate diversity metrics (unique domains, HTML patterns)

**Dataset Split**:
- Training: 80% (4000 examples)
- Validation: 10% (500 examples)
- Test: 10% (500 examples)

**Export Format** (ready for HuggingFace training):
```jsonl
{"example_html": "<html>...</html>", "expected_json": {...}}
```

**Important**: The `expected_json` field uses the exact Exa schema with fields: `url`, `title`, `text`, `author`, `published_date`, `image`, `favicon`, `id`

---

## Key Success Criteria

- ✅ 50+ unique real HTML examples from diverse Common Crawl domains (DONE)
- ⏳ 5000 total examples with programmatic variations (IN PROGRESS)
- ✅ Stable, well-defined JSON schema from Exa API (DONE)
- ✅ Messy, realistic HTML (not sanitized templates) (DONE)
- ✅ Consistent `example_html` → `expected_json` format (DONE)
- ⏳ Train/val/test splits ready for HuggingFace (TODO)

---

## Notes

This plan focuses on dataset quality and diversity, which is crucial for fine-tuning success in Task B. The synthetic variations will help the model generalize to different HTML structures while maintaining consistent output formatting.
