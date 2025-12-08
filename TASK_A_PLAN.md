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

## 6. Pilot Dataset Generation (⏳ CURRENT PHASE)

**Goal**: Create pilot dataset with iterative validation approach

**Strategy: Iterative Approach (Research-Backed Best Practice)**
- **DO NOT** jump straight to 5000 examples
- Start small, validate effectiveness, then scale
- Quality > Quantity: 30k high-quality examples beat 100k poor examples
- Prevent overfitting to synthetic augmentation patterns

### Phase 1: Pilot Dataset (500 examples)

**Split Base Examples BEFORE Augmentation** (Critical for preventing data leakage):
```
47 base examples from golden.jsonl:
├── 33 base → Training set (70%)
├── 7 base → Validation set (15%)
└── 7 base → Test set (15%)
```

**Augment ONLY Training Set**:
```
├── 330 training examples (33 base × 10 variations)
├── 7 validation examples (REAL ONLY - no augmentation)
└── 7 test examples (REAL ONLY - no augmentation)
Total: 344 examples for pilot
```

**Augmentation Strategies** (Conservative):

*High-Value Augmentations (Use)*:
- ✅ **Structural variations**: Wrapper divs (1-3 layers), change nesting depth
- ✅ **Attribute noise**: Random classes, IDs, data-* attributes (20-30% probability)
- ✅ **Template variations**: Swap semantically equivalent tags (div ↔ section, span ↔ em)
- ✅ **HTML comments**: Inject developer comments (3-10 per document)
- ✅ **Whitespace variations**: Prettify vs. minify

*Medium-Value Augmentations (Test in Ablation)*:
- ⚠️ **Style injection**: Inline CSS (may be irrelevant if model should ignore styling)
- ⚠️ **Content perturbations**: Only if text variety helps (likely not needed for extraction)

*Risky Augmentations (Avoid)*:
- ❌ **HTML corruption**: Missing tags, malformed attributes (unrealistic for production)
- ❌ **CDATA sections**: Rare in modern HTML

**Validation Requirements**:
- ✓ All JSONs match Exa schema (8 required fields)
- ✓ HTML parseable by BeautifulSoup
- ✓ `expected_json` identical across all variations of same base
- ✓ Manual spot-check 20 random samples
- ✓ HTML length within reasonable range (10K-50K characters)

### Phase 2: Pilot Training & Ablation (Task B Preview)

**Training Experiments**:
1. **Baseline**: Train on 33 real examples only (no augmentation)
2. **Full Augmentation**: Train on 330 synthetic examples
3. **Ablation Studies**: Train with each augmentation type separately

**Evaluation**:
- Evaluate ALL models on same 7 REAL validation examples
- Compare: Does augmentation beat baseline?
- Monitor: Training vs. validation loss gap (detect overfitting)
- Identify: Which augmentations actually improve performance

**Success Criteria for Phase 2**:
- Augmented model beats baseline on real validation data
- Training/validation gap reasonable (not overfitting to synthetic noise)
- At least one augmentation type shows clear improvement

### Phase 3: Iterative Scaling (Only if Phase 2 Succeeds)

**Scale to 1000 examples** (if pilot validates):
```
├── 33 base × 30 variations = 990 training examples
├── 7 real validation examples (unchanged)
└── 7 real test examples (unchanged)
```

**Scale to 5000 examples** (if 1000 shows continued improvement):
```
├── 33 base × ~150 variations = ~5000 training examples
├── 7 real validation examples (unchanged)
└── 7 real test examples (unchanged)
```

**Stopping Conditions**:
- Validation performance plateaus (diminishing returns)
- Training/validation gap increases (overfitting)
- Compute budget exhausted

---

## 7. Full Dataset Generation (Only After Validation)

**Goal**: Generate and validate complete dataset (ONLY after pilot succeeds)

**Preconditions** (Must be met before full generation):
- ✓ Pilot training (Phase 2) shows improvement over baseline
- ✓ Ablation studies identify effective augmentation strategies
- ✓ Validation performance has NOT plateaued
- ✓ Training/validation gap is reasonable (no severe overfitting)

**Generation** (If validated):
- 33 training base examples × ~150 variations = ~5000 training examples
- Use ONLY augmentation strategies proven effective in ablation studies
- Maintain same 7 real validation + 7 real test examples

**Refined Augmentation Strategy**:
- Use only augmentation types that improved validation performance
- Drop augmentations that hurt or showed no benefit
- Adjust probabilities based on ablation results
- Ensure variations span diverse structural patterns

**Validation Pipeline**:
- Verify all JSONs match Exa schema (8 required fields)
- Check HTML parsability (can be parsed by standard parsers)
- Ensure `expected_json` remains unchanged across variations
- Manual spot-check random samples
- Calculate diversity metrics (unique structural patterns)
- Run detection classifier: Real vs. Synthetic (target 60-75% accuracy)

**Final Dataset Split**:
```
Training:   ~5000 synthetic examples (33 base × ~150 variations)
Validation: 7 real examples (NO augmentation)
Test:       7 real examples (NO augmentation)
```

**Export Format** (ready for HuggingFace training):
```jsonl
{"example_html": "<html>...</html>", "expected_json": {...}}
```

**Critical Rules**:
- ❌ NEVER augment validation or test sets
- ✅ Validation/test must remain REAL examples only
- ✅ Split base examples BEFORE any augmentation
- ✅ `expected_json` must be identical across all variations of same base

**Important**: The `expected_json` field uses the exact Exa schema with fields: `url`, `title`, `text`, `author`, `published_date`, `image`, `favicon`, `id`

---

## Key Success Criteria

**Phase 1: Base Dataset (✅ COMPLETE)**
- ✅ 47 unique real HTML examples from diverse Common Crawl domains
- ✅ Stable, well-defined JSON schema from Exa API
- ✅ Messy, realistic HTML (not sanitized templates)
- ✅ Consistent `example_html` → `expected_json` format

**Phase 2: Pilot Dataset (⏳ CURRENT)**
- ⏳ 344 pilot examples (330 synthetic train + 7 real val + 7 real test)
- ⏳ Split BEFORE augmentation to prevent data leakage
- ⏳ Validation: Schema consistency, HTML parseable, spot-check quality
- ⏳ Ablation-ready structure for Task B testing

**Phase 3: Pilot Training Validation (TODO - Task B)**
- ⬜ Baseline model trained on 33 real examples only
- ⬜ Augmented model trained on 330 synthetic examples
- ⬜ Ablation studies per augmentation type
- ⬜ Augmented model beats baseline on real validation data
- ⬜ Identified effective augmentation strategies

**Phase 4: Full Dataset (TODO - Only if Phase 3 succeeds)**
- ⬜ ~5000 training examples using validated augmentation strategies
- ⬜ Same 7 real validation + 7 real test examples (unchanged)
- ⬜ Final validation: Schema, parsability, diversity metrics
- ⬜ Ready for full-scale fine-tuning in Task B

---

## Notes

### Rationale for Iterative Approach

**Research-Backed Best Practices**:
- Quality > Quantity: 30k high-quality examples outperform 100k poorly curated examples
- Iterative validation prevents overfitting to synthetic augmentation patterns
- Structured extraction tasks require less data than generation (100s often sufficient)
- Early validation prevents wasted compute on ineffective augmentations

**Risks of Jumping to Full 5000**:
- May overfit to augmentation procedure rather than real data distribution
- Cannot identify which augmentations help vs. hurt
- Waste 80% of effort if augmentations don't improve validation performance
- No opportunity to course-correct based on training feedback

**Why Split Before Augmentation**:
- Prevents data leakage between train/validation/test
- Validation/test contain only real examples to measure true generalization
- Allows measuring model's ability to handle variations of unseen base examples
- Standard best practice in ML literature

**Validation-First Philosophy**:
- Generate pilot → Train → Evaluate → Identify effective strategies → Scale
- Each scaling step requires validation on REAL data
- Stop scaling if validation plateaus (diminishing returns)
- This approach maximizes chance of success in Task B fine-tuning

### Implementation Files

- `notebooks/04_generate_synthetic.ipynb` - Exploration and pilot generation
- `scripts/04_generate.py` - Production synthetic data generation
- `scripts/verify_synthetic_dataset.py` - Dataset integrity verification
