"""
02_augment.py - Generate synthetic variations of base datasets

This script:
1. Loads train_base.jsonl, val_base.jsonl, test_base.jsonl
2. Augments train, val
4. Copies test as-is (pristine for true generalization)
5. Saves train.jsonl, val.jsonl, test.jsonl

Augmentation strategies:
- Structural variations (wrapper divs, nesting depth)
- Attribute noise (random classes, IDs, data attributes)
- Content perturbations (style injection, comments, extra whitespace)
- HTML formatting variations (whitespace, attribute order)
"""

import json
import random
import re
from pathlib import Path

from bs4 import BeautifulSoup, Comment

random.seed(42)

TRAIN_BASE_PATH = Path("data/processed/train_base.jsonl")
VAL_BASE_PATH = Path("data/processed/val_base.jsonl")
TEST_BASE_PATH = Path("data/processed/test_base.jsonl")

TRAIN_OUTPUT = Path("data/processed/train.jsonl")
VAL_OUTPUT = Path("data/processed/val.jsonl")
TEST_OUTPUT = Path("data/processed/test.jsonl")

TRAIN_TARGET_SIZE = 400
VAL_TARGET_SIZE = 50


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    with open(path) as f:
        return [json.loads(line) for line in f]


def save_jsonl(examples: list[dict], path: Path):
    """Save examples to JSONL file."""
    with open(path, "w") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")


def add_wrapper_divs(html: str, num_wrappers: int | None = None) -> str:
    """Add random wrapper div elements."""
    if num_wrappers is None:
        num_wrappers = random.randint(1, 3)

    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")

    if body:
        for _ in range(num_wrappers):
            wrapper_classes = [
                "container",
                "wrapper",
                "content",
                "main",
                "page-wrapper",
                "site-content",
                "app-root",
            ]
            wrapper = soup.new_tag("div", attrs={"class": random.choice(wrapper_classes)})

            for child in list(body.children):
                wrapper.append(child)

            body.append(wrapper)

    return str(soup)


def add_random_attributes(html: str) -> str:
    """Add random attributes to existing elements."""
    soup = BeautifulSoup(html, "html.parser")

    all_tags = soup.find_all(True)

    num_to_modify = min(len(all_tags), random.randint(5, 20))
    tags_to_modify = random.sample(all_tags, num_to_modify)

    for tag in tags_to_modify:
        if random.random() < 0.5:
            existing_classes = tag.get("class", [])
            new_classes = [*existing_classes, f"auto-{random.randint(1000, 9999)}"]
            tag["class"] = new_classes

        if random.random() < 0.3:
            tag["data-id"] = f"{random.randint(10000, 99999)}"

        if random.random() < 0.2:
            tag["aria-hidden"] = "true"

    return str(soup)


def inject_comments(html: str) -> str:
    """Inject HTML comments at random positions."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")

    if body:
        comments = [
            " Generated content ",
            " Auto-generated ",
            " SEO optimization ",
            " Analytics tracking ",
            " Ad placement ",
        ]

        for _ in range(random.randint(2, 5)):
            comment = Comment(random.choice(comments))

            all_elements = body.find_all(True)
            if all_elements:
                random_element = random.choice(all_elements)
                random_element.insert_before(comment)

    return str(soup)


def inject_styles(html: str) -> str:
    """Inject inline style tags."""
    soup = BeautifulSoup(html, "html.parser")
    head = soup.find("head")

    if head:
        style_contents = [
            ".hidden { display: none; }",
            '.clearfix::after { content: ""; display: table; clear: both; }',
            "body { margin: 0; padding: 0; }",
            "* { box-sizing: border-box; }",
        ]

        style_tag = soup.new_tag("style")
        style_tag.string = "\n".join(random.sample(style_contents, k=random.randint(1, 3)))
        head.append(style_tag)

    return str(soup)


def vary_whitespace(html: str) -> str:
    """Vary whitespace and formatting."""
    if random.random() < 0.5:
        html = re.sub(r"(<div)", r"\n\1", html)

    if random.random() < 0.5:
        html = re.sub(r"(>)(<)", r">\n<", html)

    return html


def generate_variation(base_example: dict, variation_id: int) -> dict:
    """Generate a synthetic variation of a base example."""
    html = base_example["example_html"]

    augmentations = []

    if random.random() < 0.7:
        html = add_wrapper_divs(html)
        augmentations.append("wrapper_divs")

    if random.random() < 0.6:
        html = add_random_attributes(html)
        augmentations.append("random_attrs")

    if random.random() < 0.5:
        html = inject_comments(html)
        augmentations.append("comments")

    if random.random() < 0.4:
        html = inject_styles(html)
        augmentations.append("styles")

    if random.random() < 0.5:
        html = vary_whitespace(html)
        augmentations.append("whitespace")

    variation = {
        "example_html": html,
        "expected_json": base_example["expected_json"],
        "_metadata": {
            "variation_id": variation_id,
            "augmentations": augmentations,
        },
    }

    return variation


def generate_synthetic_dataset(base_examples: list[dict], target_size: int) -> list[dict]:
    """Generate synthetic variations to reach target size."""
    synthetic_examples = []

    num_base = len(base_examples)
    variations_per_base = (target_size - num_base) // num_base
    extra_variations = (target_size - num_base) % num_base

    print(f"  Generating {variations_per_base} variations per base example")
    if extra_variations > 0:
        print(f"  Plus {extra_variations} extra variations")

    variation_id = 0

    for idx, base_example in enumerate(base_examples):
        # Include original base example
        synthetic_examples.append(base_example)

        # Generate variations
        num_variations = variations_per_base
        if idx < extra_variations:
            num_variations += 1

        for _ in range(num_variations):
            variation = generate_variation(base_example, variation_id)
            synthetic_examples.append(variation)
            variation_id += 1

    return synthetic_examples


def main():
    """Main execution."""
    print("Loading base datasets...")
    train_base = load_jsonl(TRAIN_BASE_PATH)
    val_base = load_jsonl(VAL_BASE_PATH)
    test_base = load_jsonl(TEST_BASE_PATH)

    print(f"Train base: {len(train_base)} examples")
    print(f"Val base:   {len(val_base)} examples")
    print(f"Test base:  {len(test_base)} examples")

    print(f"Augmenting training set to ~{TRAIN_TARGET_SIZE} examples...")
    train_augmented = generate_synthetic_dataset(train_base, target_size=TRAIN_TARGET_SIZE)
    print(f"Generated {len(train_augmented)} training examples")

    print(f"Augmenting validation set to ~{VAL_TARGET_SIZE} examples...")
    val_augmented = generate_synthetic_dataset(val_base, target_size=VAL_TARGET_SIZE)
    print(f"Generated {len(val_augmented)} validation examples")

    print(f"Test set: {len(test_base)} examples (no augmentation)")

    print("Saving augmented datasets...")
    save_jsonl(train_augmented, TRAIN_OUTPUT)
    save_jsonl(val_augmented, VAL_OUTPUT)
    save_jsonl(test_base, TEST_OUTPUT)

    print(f"Train: {TRAIN_OUTPUT} ({len(train_augmented)} examples)")
    print(f"Val:   {VAL_OUTPUT} ({len(val_augmented)} examples)")
    print(f"Test:  {TEST_OUTPUT} ({len(test_base)} examples)")

    print(f"Training examples:   {len(train_augmented)} (augmented)")
    print(f"Validation examples: {len(val_augmented)} (augmented)")
    print(f"Test examples:       {len(test_base)} (pristine - no augmentation)")
    print(f"Total examples:      {len(train_augmented) + len(val_augmented) + len(test_base)}")


if __name__ == "__main__":
    main()
