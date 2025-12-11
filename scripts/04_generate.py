"""
04_generate.py - Generate synthetic variations of golden dataset

This script will:
1. Load the golden dataset (data/processed/golden.jsonl)
2. Hold out test set (50 examples) - never used for training
3. Generate synthetic variations from remaining (47 examples) to reach 450 total
4. Split synthetic into train (400) and validation (50)
5. Save train, val, and test splits

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
from typing import Dict, List

from bs4 import BeautifulSoup, Comment


random.seed(42)


def load_golden_dataset(path: Path) -> List[Dict]:
    """Load golden dataset from JSONL."""
    with open(path) as f:
        return [json.loads(line) for line in f]


def split_test_set(examples: List[Dict], test_size: int = 50) -> tuple:
    """Split out test set as holdout."""
    shuffled = examples.copy()
    random.shuffle(shuffled)

    test_examples = shuffled[:test_size]
    remaining = shuffled[test_size:]

    return remaining, test_examples


def add_wrapper_divs(html: str, num_wrappers: int = None) -> str:
    """Add random wrapper div elements."""
    if num_wrappers is None:
        num_wrappers = random.randint(1, 3)

    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')

    if body:
        for _ in range(num_wrappers):
            wrapper_classes = [
                'container', 'wrapper', 'content', 'main',
                'page-wrapper', 'site-content', 'app-root'
            ]
            wrapper = soup.new_tag('div', attrs={'class': random.choice(wrapper_classes)})

            for child in list(body.children):
                wrapper.append(child)

            body.append(wrapper)

    return str(soup)


def add_random_attributes(html: str) -> str:
    """Add random attributes to existing elements."""
    soup = BeautifulSoup(html, 'html.parser')

    all_tags = soup.find_all(True)

    num_to_modify = min(len(all_tags), random.randint(5, 20))
    tags_to_modify = random.sample(all_tags, num_to_modify)

    for tag in tags_to_modify:
        if random.random() < 0.5:
            existing_classes = tag.get('class', [])
            new_classes = existing_classes + [f'auto-{random.randint(1000, 9999)}']
            tag['class'] = new_classes

        if random.random() < 0.3:
            tag[f'data-id'] = f'{random.randint(10000, 99999)}'

        if random.random() < 0.2:
            tag['aria-hidden'] = 'true'

    return str(soup)


def inject_comments(html: str) -> str:
    """Inject HTML comments at random positions."""
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')

    if body:
        comments = [
            ' Generated content ',
            ' Auto-generated ',
            ' SEO optimization ',
            ' Analytics tracking ',
            ' Ad placement ',
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
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')

    if head:
        style_contents = [
            '.hidden { display: none; }',
            '.clearfix::after { content: ""; display: table; clear: both; }',
            'body { margin: 0; padding: 0; }',
            '* { box-sizing: border-box; }',
        ]

        style_tag = soup.new_tag('style')
        style_tag.string = '\n'.join(random.sample(style_contents, k=random.randint(1, 3)))
        head.append(style_tag)

    return str(soup)


def vary_whitespace(html: str) -> str:
    """Vary whitespace and formatting."""
    if random.random() < 0.5:
        html = re.sub(r'(<div)', r'\n\1', html)

    if random.random() < 0.5:
        html = re.sub(r'(>)(<)', r'>\n<', html)

    return html


def generate_variation(base_example: Dict, variation_id: int) -> Dict:
    """Generate a synthetic variation of a base example."""
    html = base_example['example_html']

    augmentations = []

    if random.random() < 0.7:
        html = add_wrapper_divs(html)
        augmentations.append('wrapper_divs')

    if random.random() < 0.6:
        html = add_random_attributes(html)
        augmentations.append('random_attrs')

    if random.random() < 0.5:
        html = inject_comments(html)
        augmentations.append('comments')

    if random.random() < 0.4:
        html = inject_styles(html)
        augmentations.append('styles')

    if random.random() < 0.5:
        html = vary_whitespace(html)
        augmentations.append('whitespace')

    variation = {
        'example_html': html,
        'expected_json': base_example['expected_json'],
        '_metadata': {
            'variation_id': variation_id,
            'base_url': base_example['expected_json']['url'],
            'augmentations': augmentations,
        },
    }

    return variation


def generate_synthetic_dataset(base_examples: List[Dict], target_size: int) -> List[Dict]:
    """Generate synthetic variations to reach target size."""
    synthetic_examples = []

    num_base = len(base_examples)
    variations_per_base = (target_size - num_base) // num_base
    extra_variations = (target_size - num_base) % num_base

    print(f"Generating {variations_per_base} variations per base example")
    print(f"Plus {extra_variations} extra variations")

    variation_id = 0

    for idx, base_example in enumerate(base_examples):
        synthetic_examples.append(base_example)

        num_variations = variations_per_base
        if idx < extra_variations:
            num_variations += 1

        for _ in range(num_variations):
            variation = generate_variation(base_example, variation_id)
            synthetic_examples.append(variation)
            variation_id += 1

    return synthetic_examples


def save_dataset(examples: List[Dict], path: Path, strip_metadata: bool = True):
    """Save dataset to JSONL."""
    with open(path, 'w') as f:
        for example in examples:
            if strip_metadata and '_metadata' in example:
                example_copy = {k: v for k, v in example.items() if k != '_metadata'}
                f.write(json.dumps(example_copy) + '\n')
            else:
                f.write(json.dumps(example) + '\n')


def split_train_val(examples: List[Dict], train_size: int = 400, val_size: int = 50) -> tuple:
    """Split synthetic examples into train and val."""
    shuffled = examples.copy()
    random.shuffle(shuffled)

    train_examples = shuffled[:train_size]
    val_examples = shuffled[train_size:train_size + val_size]

    return train_examples, val_examples


def main():
    """Main execution."""
    golden_path = Path("data/processed/golden.jsonl")
    train_path = Path("data/processed/train.jsonl")
    val_path = Path("data/processed/val.jsonl")
    test_path = Path("data/processed/test.jsonl")

    print("Loading golden dataset...")
    golden_examples = load_golden_dataset(golden_path)
    print(f"Total golden examples: {len(golden_examples)}")

    print("\nHolding out test set...")
    remaining, test_examples = split_test_set(golden_examples, test_size=50)
    print(f"Test holdout: {len(test_examples)} examples")
    print(f"Remaining for training: {len(remaining)} examples")

    target_synthetic_size = 450
    print(f"\nGenerating {target_synthetic_size} synthetic examples from {len(remaining)} base examples...")
    synthetic_examples = generate_synthetic_dataset(remaining, target_synthetic_size)
    print(f"Total synthetic examples: {len(synthetic_examples)}")

    print(f"\nSplitting synthetic into train/val...")
    train_examples, val_examples = split_train_val(synthetic_examples, train_size=400, val_size=50)
    print(f"Train: {len(train_examples)} examples")
    print(f"Validation: {len(val_examples)} examples")

    print("\nSaving datasets...")
    save_dataset(train_examples, train_path, strip_metadata=True)
    save_dataset(val_examples, val_path, strip_metadata=True)
    save_dataset(test_examples, test_path, strip_metadata=True)

    print(f"✓ Training set: {train_path} ({len(train_examples)} examples)")
    print(f"✓ Validation set: {val_path} ({len(val_examples)} examples)")
    print(f"✓ Test set: {test_path} ({len(test_examples)} examples)")

    print("\n" + "="*60)
    print("DATASET GENERATION COMPLETE")
    print("="*60)
    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(val_examples)}")
    print(f"Test examples: {len(test_examples)}")
    print(f"Total examples: {len(train_examples) + len(val_examples) + len(test_examples)}")


if __name__ == "__main__":
    main()
