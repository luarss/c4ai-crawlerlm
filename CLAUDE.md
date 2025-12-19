# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CrawlerLM is a synthetic dataset generation and model fine-tuning pipeline for training small language models to extract structured JSON from HTML. The project implements an end-to-end pipeline: sample HTML from Common Crawl → filter for quality → extract structured data → generate synthetic variations → convert to chat format → fine-tune models.

**Current Status**: Task A (synthetic dataset generation) is complete with train/val/test splits generated. Task B (fine-tuning) and Task C (evaluation) are next phases.

## Code Style Guidelines

**IMPORTANT: NO EMOJIS IN CODE OR DOCUMENTATION**

This repository has a strict no-emoji policy:
- NEVER use emojis in Python code, JavaScript, HTML, or any source files
- NEVER use emojis in markdown documentation (.md files)
- NEVER use emojis in comments, docstrings, or commit messages
- Use plain text alternatives instead (e.g., "Success:", "Error:", "Warning:")
- Exception: Data files (JSON annotations, HTML files in `/data/`) may contain emojis if they are part of actual webpage content being processed

## Development Commands

### Environment Setup
```bash
# Install dependencies (uses uv package manager)
uv sync --all-extras

# Set up API key (required for 02_fetch.py)
cp .env.example .env
# Edit .env and add your EXA_API_KEY
```

### Running the Pipeline

The scripts are numbered in execution order (00 → 05):

```bash
# 1. Sample URLs from Common Crawl index
python scripts/00_sample.py

# 2. Filter for quality (static pages, no SPAs/errors)
python scripts/01_filter.py

# 3. Fetch structured data using Exa API (requires EXA_API_KEY in .env)
python scripts/02_fetch.py

# 4. Join HTML with JSON extracts into golden.jsonl
python scripts/03_join.py

# 5. Generate synthetic variations (train/val/test splits)
python scripts/04_generate.py

# 6. Convert to chat format for fine-tuning
python scripts/05_convert_to_chat_format.py

# 7. Push to HuggingFace Hub
python scripts/push_to_hf.py <username/dataset-name> [--private]
```

### Notebooks

Exploratory analysis and prototyping notebooks are in `notebooks/`:
- `00_eda.ipynb` - Exploratory data analysis
- `04_generate_synthetic.ipynb` - Synthetic data generation experimentation

## Architecture

### Pipeline Flow

```
Common Crawl Index
    ↓ 00_sample.py (diversity sampling)
Raw URL candidates (~400)
    ↓ 01_filter.py (SPA detection, quality scoring)
Selected URLs (50 best)
    ↓ 02_fetch.py (Exa API extraction)
JSON extracts
    ↓ 03_join.py (match HTML with JSON)
Golden dataset (golden.jsonl)
    ↓ 04_generate.py (synthetic augmentation)
Train/Val/Test splits
    ↓ 05_convert_to_chat_format.py
Chat format datasets (*_chat.jsonl)
    ↓ push_to_hf.py
HuggingFace Dataset
```

### Data Schema

**Golden Dataset Format** (`data/processed/golden.jsonl`):
```json
{
  "example_html": "<html>...</html>",
  "expected_json": {
    "url": "https://...",
    "title": "Page Title",
    "text": "Extracted content in markdown",
    "author": "Author Name or null",
    "published_date": "2024-01-01 or null",
    "image": "https://... or null",
    "favicon": "https://... or null",
    "id": "unique-identifier"
  }
}
```

The `expected_json` schema is defined by the Exa API and cannot be modified.

**Chat Format** (`*_chat.jsonl`):
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Extract structured data from the following HTML...\n\nHTML:\n<html>..."
    },
    {
      "role": "assistant",
      "content": "{\"url\": \"...\", \"title\": \"...\", ...}"
    }
  ]
}
```

### Data Splits Strategy

Critical design decision to prevent data leakage:

1. **Split BEFORE augmentation**: The 47 base examples from `golden.jsonl` are split into train/val/test sets FIRST
2. **Augment ONLY training set**: Synthetic variations are generated only from training base examples
3. **Val/test remain real**: Validation and test sets contain only real, unaugmented HTML examples

This ensures the model is evaluated on genuinely unseen data distributions, not just variations of training examples.

### Synthetic Augmentation Strategies

Implemented in `scripts/04_generate.py`:

**High-value augmentations** (currently used):
- Structural variations: Add wrapper divs (1-3 layers), change nesting depth
- Attribute noise: Random classes, IDs, data-* attributes
- Template variations: Swap semantically equivalent tags (div ↔ section)
- HTML comments: Inject developer comments
- Whitespace variations: Prettify vs. minify

**Conservative approach**: The augmentation strategy is designed to create realistic HTML variations while preserving the semantic content and ensuring `expected_json` remains unchanged across all variations of the same base example.

## Key Implementation Details

### Quality Filtering (01_filter.py)

The filtering script implements sophisticated heuristics to select high-quality HTML:

- **SPA Detection**: Identifies React, Vue, Angular, Nuxt apps by framework signatures and low text-to-HTML ratios
- **Anomaly Detection**: Filters out error pages, redirects, login walls, captchas, bot blocks
- **Content Scoring**: Evaluates text density, HTML structure, token count (target: 4K-128K tokens)
- **Domain Diversity**: Ensures diverse domains using hash-based sampling

### Exa API Integration (02_fetch.py)

- Uses parallel batch processing (5 workers by default)
- Tracks API costs per request
- Extracts structured data following Exa's fixed schema
- Saves results to `data/fetched/exa_contents.json`

### URL Matching (03_join.py)

Implements robust URL normalization to handle http/https and trailing slash variations:
- Lowercase domains
- Remove trailing slashes
- Scheme-agnostic matching

### HuggingFace Upload (push_to_hf.py)

Supports both full dataset upload and README-only updates:
```bash
# Upload full dataset
python scripts/push_to_hf.py username/dataset-name [--private]

# Update README only
python scripts/push_to_hf.py username/dataset-name --readme-only
```

## File Structure

```
data/
  fetched/             # Exa API extraction results
  processed/           # Final datasets
    golden.jsonl       # Base dataset (47 examples)
    train.jsonl        # Training set (~400 synthetic examples)
    val.jsonl          # Validation set (7 real examples)
    test.jsonl         # Test set (7 real examples)
    train_chat.jsonl   # Chat-formatted training data
    val_chat.jsonl     # Chat-formatted validation data
    test_chat.jsonl    # Chat-formatted test data
  selected_url_list.txt  # Filtered URL list (50 URLs)
  README.md           # HuggingFace dataset card

notebooks/            # Jupyter notebooks for exploration
scripts/              # Production pipeline scripts (00-05)
```

## Dependencies

This project uses Python 3.13 and `uv` for dependency management.

**Core dependencies** (defined in `pyproject.toml`):
- `httpx` - HTTP client for API calls
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management
- `exa-py` - Exa API client for structured extraction
- `beautifulsoup4` - HTML parsing
- `tqdm` - Progress bars

**Dev dependencies** (`[project.optional-dependencies]`):
- `notebook` - Jupyter notebooks
- `pandas`, `matplotlib`, `seaborn` - Data analysis and visualization
- `tiktoken` - Token counting for quality filtering
- `langdetect` - Language detection
- `huggingface-hub`, `datasets` - HuggingFace integration

## Task Context

This project implements Task A from the problem statement:

**Goal**: Generate a synthetic dataset of 5k HTML → JSON examples for fine-tuning small language models.

**Requirements**:
- 50-100 real HTML examples from Common Crawl (messy, inconsistent, nested)
- Programmatic synthetic variations to reach 5k examples
- Stable JSON schema (Exa format with 8 required fields)
- Train/val/test splits with proper data leakage prevention

**Next phases**:
- Task B: Fine-tune a small model (e.g., Qwen 0.6B) using HuggingFace training pipeline
- Task C: Write findings summary comparing baseline vs. fine-tuned performance

See `TASK_A_PLAN.md` for detailed planning rationale and iterative validation approach.
