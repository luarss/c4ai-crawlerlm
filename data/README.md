---
task_categories:
- text-generation
- information-extraction
language:
- en
size_categories:
- n<1K
tags:
- web-scraping
- html-extraction
- structured-data
- synthetic-data
---

# CrawlerLM: HTML Fragment to Structured JSON

A synthetic dataset for training language models to extract structured JSON from HTML fragments across multiple schema types.

## Dataset Description

This dataset contains HTML fragments paired with structured JSON annotations across three schema types: **recipes**, **job postings**, and **events**. It's designed for fine-tuning small language models to perform domain-specific information extraction from messy, real-world HTML.

### Key Features

- **60 manually annotated base examples** from diverse web sources
- **3 schema types** with domain-specific fields
- **Synthetic augmentation** to 447+ training examples with realistic HTML variations
- **Two configurations**: raw (HTML→JSON) and chat (instruction format)
- **Token-filtered** (all examples ≤24K tokens)

## Configurations

### `raw` Configuration

HTML fragment to JSON extraction format.

**Fields**:
- `example_html` (string): Raw HTML fragment
- `expected_json` (dict): Structured extraction with schema-specific fields

**Example**:
```python
{
  "example_html": "<div class=\"recipe-card\">...</div>",
  "expected_json": {
    "type": "recipe",
    "title": "Best Ever Macaroni Cheese",
    "ingredients": ["500g macaroni", "200g cheddar", ...],
    "instructions": ["Boil pasta", "Make sauce", ...],
    "prep_time": "10 mins",
    "cook_time": "20 mins",
    ...
  }
}
```

**Splits**:
- Train: 400 examples (augmented from 48 base examples)
- Validation: 50 examples (augmented from 6 base examples)
- Test: 6 examples (pristine, no augmentation)

### `chat` Configuration

Instruction-tuning format for training chat models.

**Fields**:
- `messages` (list): Conversational format with user/assistant roles

**Example**:
```python
{
  "messages": [
    {
      "role": "user",
      "content": "Extract structured data from the following HTML and return it as JSON.\n\nHTML:\n<div>...</div>"
    },
    {
      "role": "assistant",
      "content": "{\"type\": \"recipe\", \"title\": \"...\", ...}"
    }
  ]
}
```

**Splits**:
- Train: 391 examples (9 filtered out for exceeding token limit)
- Validation: 50 examples
- Test: 6 examples

## Schema Types

### Recipe (`type: "recipe"`)

**Fields**: `type`, `title`, `description`, `ingredients`, `instructions`, `prep_time`, `cook_time`, `total_time`, `servings`, `cuisine`, `difficulty`, `rating`, `author`, `image_url`, `video_url`, `source_url`, `published_date`

**Use case**: Extracting recipe data from food blogs, cooking sites

**Example sources**: BBC Good Food, AllRecipes, Serious Eats

### Job Posting (`type: "job_posting"`)

**Fields**: `type`, `title`, `company`, `location`, `compensation`, `benefits`, `mode_of_work`, `job_type`, `experience_level`, `requirements`, `responsibilities`, `description`, `application_url`, `company_logo`, `source_url`

**Use case**: Parsing job listings from career pages, job boards

**Example sources**: Greenhouse, Lever, LinkedIn Jobs

### Event (`type: "event"`)

**Fields**: `type`, `title`, `description`, `datetime`, `end_datetime`, `location`, `venue`, `organizer`, `price`, `registration_url`, `image_url`, `category`, `tags`, `source_url`

**Use case**: Extracting event details from event listings, calendars

**Example sources**: Eventbrite, Meetup, local event pages

## Data Collection Process

1. **Manual Annotation**: 61 HTML fragments manually annotated using custom Chrome extension
2. **Quality Filtering**: Removed 1 example exceeding 24K token limit (60 examples remaining)
3. **Stratified Split**: 80/10/10 split by schema type (48 train / 6 val / 6 test base examples)
4. **Synthetic Augmentation**:
   - Train: ~8 variations per base example (400 total)
   - Val: ~8 variations per base example (50 total)
   - Test: No augmentation (6 pristine examples)
5. **Chat Conversion**: Convert to instruction-tuning format with token filtering

### Augmentation Strategies

- **Structural variations**: Wrapper divs, nesting depth changes
- **Attribute noise**: Random classes, IDs, data-* attributes
- **Template variations**: Semantically equivalent tags (div ↔ section)
- **HTML comments**: Developer comments injection
- **Whitespace variations**: Minified vs. prettified formatting

All augmentations preserve semantic content and ensure `expected_json` remains unchanged.

## Usage

### Load Raw Configuration

```python
from datasets import load_dataset

# Load raw HTML→JSON format
dataset = load_dataset("espsluar/crawlerlm-html-to-json", "raw")

train_data = dataset["train"]
val_data = dataset["validation"]
test_data = dataset["test"]

# Inspect example
example = train_data[0]
print(f"Schema type: {example['expected_json']['type']}")
print(f"HTML length: {len(example['example_html'])} chars")
print(f"Title: {example['expected_json']['title']}")
```

### Load Chat Configuration

```python
from datasets import load_dataset

# Load chat format for instruction tuning
dataset = load_dataset("espsluar/crawlerlm-html-to-json", "chat")

train_data = dataset["train"]

# Inspect example
example = train_data[0]
print(f"User prompt: {example['messages'][0]['content'][:100]}...")
print(f"Assistant response: {example['messages'][1]['content'][:100]}...")
```

### Filter by Schema Type

```python
# Filter for only recipes
recipes = dataset["train"].filter(
    lambda x: '"type": "recipe"' in x["messages"][1]["content"]
)

print(f"Recipe examples: {len(recipes)}")
```

## Dataset Statistics

| Split | Raw Examples | Chat Examples | Schema Distribution |
|-------|--------------|---------------|---------------------|
| Train | 400 | 391 | ~133 recipe, ~150 job_posting, ~117 event |
| Validation | 50 | 50 | ~17 recipe, ~17 job_posting, ~16 event |
| Test | 6 | 6 | 2 recipe, 2 job_posting, 2 event |

**Schema Distribution** (base examples before augmentation):
- Recipe: 19 examples (31.7%)
- Job Posting: 22 examples (36.7%)
- Event: 19 examples (31.7%)

## Intended Use

### Primary Use Cases

- Fine-tuning small language models (0.5B-7B parameters) for HTML extraction
- Training domain-specific web scrapers
- Benchmarking structured data extraction performance
- Teaching models to handle messy, real-world HTML

### Out of Scope

- Full webpage extraction (this dataset focuses on **fragments**, not entire pages)
- Single-field extraction (schemas have 10-17 fields each)
- Non-English content
- Dynamic/JavaScript-rendered content

## Limitations

- **Limited schema types**: Only 3 schema types (recipe, job_posting, event)
- **English only**: All examples are from English-language websites
- **Static HTML**: No JavaScript-rendered or dynamic content
- **Token limit**: All examples ≤24K tokens (may not represent very long pages)
- **Augmentation artifacts**: Synthetic variations may not perfectly match real-world HTML diversity

## Ethical Considerations

- **Web scraping**: This dataset is intended for educational and research purposes. Users should respect robots.txt and website terms of service when deploying trained models.
- **Data sources**: All HTML fragments are from publicly accessible websites
- **Privacy**: No personally identifiable information (PII) is intentionally included

## Citation

```bibtex
@misc{crawlerlm2025,
  author = {Jack Luar},
  title = {CrawlerLM: HTML Fragment to Structured JSON},
  year = {2025},
  publisher = {HuggingFace},
  howpublished = {\url{https://huggingface.co/datasets/espsluar/crawlerlm-html-to-json}}
}
```

## License

MIT

## Dataset Creation

**Tooling**: Custom Chrome extension for manual annotation ([github.com/espsluar/c4ai-crawlerlm](https://github.com/espsluar/c4ai-crawlerlm))

**Pipeline**:
1. Manual HTML fragment selection and annotation
2. Schema-specific field extraction
3. Quality filtering (token limits, validation)
4. Stratified train/val/test split
5. Synthetic augmentation (structural, attribute, whitespace variations)
6. Chat format conversion with instruction templates

**Quality Control**:
- Manual review of all base annotations
- Token count validation (≤24K per example)
- Schema validation (required fields, types)
- Stratified sampling to ensure balanced schema distribution
