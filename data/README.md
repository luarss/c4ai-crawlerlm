---
task_categories:
- text-generation
- question-answering
language:
- en
size_categories:
- n<1K
---

# CrawlerLM: HTML-to-JSON Dataset

A synthetic dataset for training language models to extract structured JSON data from raw HTML.

## Dataset Description

This dataset contains HTML pages paired with their structured JSON representations, designed for fine-tuning small language models for web scraping and information extraction tasks.

### Dataset Structure

Each example contains:
- `example_html`: Raw HTML content from real web pages
- `expected_json`: Structured extraction with fields:
  - `url`: Page URL
  - `title`: Page title
  - `text`: Main text content
  - `author`: Author name (or null)
  - `published_date`: Publication date (or null)
  - `image`: Main image URL
  - `favicon`: Favicon URL
  - `id`: Unique identifier

### Data Splits

- **Train**: 450 synthetic variations
- **Test**: 50 synthetic variations

### Data Sources

- Base HTML samples from Common Crawl
- Structured extractions via Exa API
- Synthetic variations generated programmatically

### Use Cases

- Fine-tuning small models for web scraping
- Training HTML-to-JSON extraction models
- Benchmarking structured data extraction

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("espsluar/crawlerlm-html-to-json")

# Access splits
train_data = dataset["train"]
test_data = dataset["test"]

# Example
example = train_data[0]
print(f"HTML length: {len(example['example_html'])} chars")
print(f"Title: {example['expected_json']['title']}")
```

## Dataset Creation

Generated using the CrawlerLM pipeline:
1. Sample diverse URLs from Common Crawl
2. Filter for quality (SPA detection, content scoring)
3. Extract structured data via Exa API
4. Generate synthetic variations (wrappers, noise, perturbations)

## License

MIT

## Citation

```bibtex
@misc{crawlerlm2025,
  author = {Jack Luar},
  title = {CrawlerLM: HTML-to-JSON Dataset},
  year = {2025},
  publisher = {HuggingFace},
  howpublished = {\url{https://huggingface.co/datasets/espsluar/crawlerlm-html-to-json}}
}
```
