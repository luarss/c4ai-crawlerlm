"""
01_split.py - Stratified train/val/test split, Split BEFORE augmentation to prevent data leakage.

This script:
1. Loads golden.jsonl
2. Groups by schema type
3. Performs stratified split
4. Outputs train_base.jsonl, val_base.jsonl, test_base.jsonl
"""

import json
import random
from collections import Counter
from pathlib import Path

from sklearn.model_selection import train_test_split

GOLDEN_PATH = Path("data/processed/golden.jsonl")
TRAIN_OUTPUT = Path("data/processed/train_base.jsonl")
VAL_OUTPUT = Path("data/processed/val_base.jsonl")
TEST_OUTPUT = Path("data/processed/test_base.jsonl")

RANDOM_SEED = 42
TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1

random.seed(RANDOM_SEED)


def load_golden(path: Path) -> list[dict]:
    """Load golden dataset from JSONL."""
    examples = []
    with open(path) as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def get_schema_types(examples: list[dict]) -> list[str]:
    """Extract schema type from each example."""
    return [ex["expected_json"]["type"] for ex in examples]


def save_jsonl(examples: list[dict], path: Path):
    """Save examples to JSONL file."""
    with open(path, "w") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")


def main():
    """Main execution."""
    print(f"Loading {GOLDEN_PATH}...")
    examples = load_golden(GOLDEN_PATH)
    print(f"Loaded {len(examples)} examples")

    schema_types = get_schema_types(examples)
    type_counts = Counter(schema_types)

    print("Schema type distribution:")
    for schema_type, count in sorted(type_counts.items()):
        print(f"  {schema_type}: {count}")

    print(f"Performing stratified split (train ratio: {TRAIN_RATIO})...")
    train_examples, temp_examples, _train_types, temp_types = train_test_split(
        examples,
        schema_types,
        train_size=TRAIN_RATIO,
        test_size=1 - TRAIN_RATIO,
        stratify=schema_types,
        random_state=RANDOM_SEED,
    )

    print(f"Train: {len(train_examples)} examples")
    print(f"Temp: {len(temp_examples)} examples")

    val_test_total = VAL_RATIO + TEST_RATIO
    val_proportion = VAL_RATIO / val_test_total
    print(f"Splitting temp into val/test (val: {VAL_RATIO}, test: {TEST_RATIO})...")
    val_examples, test_examples, _, _ = train_test_split(
        temp_examples,
        temp_types,
        train_size=val_proportion,
        test_size=1 - val_proportion,
        stratify=temp_types,
        random_state=RANDOM_SEED,
    )

    print(f"Val: {len(val_examples)} examples")
    print(f"Test: {len(test_examples)} examples")

    total = len(train_examples) + len(val_examples) + len(test_examples)
    assert total == len(examples), f"Split total mismatch: {total} != {len(examples)}"

    print("Split distribution by schema type:")
    train_type_counts = Counter(get_schema_types(train_examples))
    val_type_counts = Counter(get_schema_types(val_examples))
    test_type_counts = Counter(get_schema_types(test_examples))

    for schema_type in sorted(type_counts.keys()):
        print(f"  {schema_type}:")
        print(f"    Train: {train_type_counts.get(schema_type)}")
        print(f"    Val:   {val_type_counts.get(schema_type)}")
        print(f"    Test:  {test_type_counts.get(schema_type)}")
        print(f"    Total: {type_counts[schema_type]}")

    print("Saving splits...")
    save_jsonl(train_examples, TRAIN_OUTPUT)
    save_jsonl(val_examples, VAL_OUTPUT)
    save_jsonl(test_examples, TEST_OUTPUT)

    print(f"Train: {TRAIN_OUTPUT} ({len(train_examples)} examples)")
    print(f"Val:   {VAL_OUTPUT} ({len(val_examples)} examples)")
    print(f"Test:  {TEST_OUTPUT} ({len(test_examples)} examples)")

    print(f"Total examples: {total}")
    print(f"Train: {len(train_examples)} ({len(train_examples) / total * 100:.1f}%)")
    print(f"Val:   {len(val_examples)} ({len(val_examples) / total * 100:.1f}%)")
    print(f"Test:  {len(test_examples)} ({len(test_examples) / total * 100:.1f}%)")
    print("These are BASE splits - augmentation happens in next step!")


if __name__ == "__main__":
    main()
