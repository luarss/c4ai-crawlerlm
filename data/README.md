---
task_categories:
- text-generation
language:
- en
size_categories:
- n<1K
tags:
- web-scraping
- html-extraction
- structured-data
- synthetic-data
- instruction-tuning
---

# CrawlerLM: HTML to JSON Extraction

A synthetic instruction-tuning dataset for training language models to extract structured JSON from HTML.

## Dataset Description

This dataset contains HTML paired with structured JSON extraction tasks in chat format. It's designed for fine-tuning small language models to perform structured data extraction from messy, real-world HTML across multiple domains.

### Key Features

- **447 examples** in instruction-tuning chat format
- **Real HTML** from diverse web sources (recipes, job postings, events)
- **Synthetic augmentation** with realistic HTML variations
- **Clean splits**: train (391) / validation (50) / test (6)

## Dataset Format

All examples are in instruction-tuning chat format with user/assistant messages.

**Fields**:
- `messages` (list): Conversational format with user/assistant roles
  - User message: Instruction + HTML input
  - Assistant message: JSON output

**Example**:
```python
{
  "messages": [
    {
      "role": "user",
      "content": "Extract structured data from the following HTML and return it as JSON.\n\nHTML:\n<div class=\"recipe-card\">...</div>"
    },
    {
      "role": "assistant",
      "content": "{\"type\": \"recipe\", \"title\": \"Best Ever Macaroni Cheese\", \"ingredients\": [\"500g macaroni\", ...], ...}"
    }
  ]
}
```

**Splits**:
- Train: 391 examples
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

1. **Manual Annotation**: HTML fragments manually annotated using custom Chrome extension
2. **Quality Filtering**: Token limit filtering and validation
3. **Stratified Split**: Train/val/test split by schema type before augmentation
4. **Synthetic Augmentation**: Generate HTML variations while preserving JSON semantics
5. **Chat Conversion**: Convert to instruction-tuning format with system prompt

### Augmentation Strategies

- **Structural variations**: Wrapper divs, nesting depth changes
- **Attribute noise**: Random classes, IDs, data-* attributes
- **Template variations**: Semantically equivalent tags (div ↔ section)
- **HTML comments**: Developer comments injection
- **Whitespace variations**: Minified vs. prettified formatting

All augmentations preserve semantic content and ensure `expected_json` remains unchanged.

## Usage

### Load Dataset

```python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("espsluar/crawlerlm-html-to-json")

train_data = dataset["train"]
val_data = dataset["validation"]
test_data = dataset["test"]

# Inspect example
example = train_data[0]
print(f"User prompt: {example['messages'][0]['content'][:100]}...")
print(f"Assistant response: {example['messages'][1]['content'][:100]}...")
```

### Filter by Schema Type

```python
from datasets import load_dataset

dataset = load_dataset("espsluar/crawlerlm-html-to-json")

# Filter for only recipes
recipes = dataset["train"].filter(
    lambda x: '"type": "recipe"' in x["messages"][1]["content"]
)

print(f"Recipe examples: {len(recipes)}")
```

### Fine-tuning Example

```python
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments

# Load dataset
dataset = load_dataset("espsluar/crawlerlm-html-to-json")

# Load model and tokenizer
model_name = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Apply chat template and tokenize
def format_example(example):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False
    )
    return tokenizer(text, truncation=True, max_length=4096)

tokenized_dataset = dataset.map(format_example, remove_columns=["messages"])

# Train
trainer = Trainer(
    model=model,
    args=TrainingArguments(
        output_dir="./crawlerlm-finetuned",
        per_device_train_batch_size=1,
        num_train_epochs=3,
    ),
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
)

trainer.train()
```

## Dataset Statistics

| Split | Examples | Schema Distribution |
|-------|----------|---------------------|
| Train | 391 | ~133 recipe, ~150 job_posting, ~117 event |
| Validation | 50 | ~17 recipe, ~17 job_posting, ~16 event |
| Test | 6 | 2 recipe, 2 job_posting, 2 event |
| **Total** | **447** | |

**Schema Distribution**:
- Recipe: ~152 examples (34%)
- Job Posting: ~169 examples (38%)
- Event: ~135 examples (30%)

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
- **Moderate dataset size**: 447 examples total (391 training examples)
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
