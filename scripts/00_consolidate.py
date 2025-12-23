"""
00_consolidate.py - Consolidate manual annotations into golden dataset

This script:
1. Reads all annotation_*.json files from data/manual/
2. Validates structure (example_html, expected_json with type field)
3. Aggregates into data/processed/golden.jsonl
4. Reports statistics by schema type
"""

import json
from collections import Counter
from pathlib import Path

MANUAL_DIR = Path("data/manual")
OUTPUT_PATH = Path("data/processed/golden.jsonl")


def load_annotation(file_path: Path) -> dict:
    """Load and validate a single annotation file."""
    with open(file_path) as f:
        data = json.load(f)

    # Validate required keys
    if "example_html" not in data:
        raise ValueError(f"{file_path}: Missing 'example_html' key")
    if "expected_json" not in data:
        raise ValueError(f"{file_path}: Missing 'expected_json' key")
    if "type" not in data["expected_json"]:
        raise ValueError(f"{file_path}: Missing 'type' in expected_json")

    return data


def main():
    """Main execution."""
    annotation_files = sorted(MANUAL_DIR.glob("annotation_*.json"))
    print(f"Found {len(annotation_files)} annotation files in {MANUAL_DIR}")

    if len(annotation_files) == 0:
        print(f"No annotation files found in {MANUAL_DIR}")
        return

    print("Loading and validating annotations...")
    annotations = []
    schema_types = []
    errors = []

    for file_path in annotation_files:
        try:
            data = load_annotation(file_path)
            annotations.append(data)
            schema_types.append(data["expected_json"]["type"])
        except Exception as e:
            errors.append(f"  {file_path.name}: {e}")

    if errors:
        print("Errors encountered:")
        for error in errors:
            print(error)
        print(f"{len(errors)} files failed validation")

    print(f"Successfully loaded {len(annotations)} annotations")

    type_counts = Counter(schema_types)
    print("Schema type distribution:")
    for schema_type, count in sorted(type_counts.items()):
        print(f"  {schema_type}: {count}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing to {OUTPUT_PATH}...")

    with open(OUTPUT_PATH, "w") as f:
        for annotation in annotations:
            f.write(json.dumps(annotation, ensure_ascii=False) + "\n")

    print(f"Wrote {len(annotations)} examples to {OUTPUT_PATH}")
    print(f"Total examples: {len(annotations)}")
    print(f"Output file: {OUTPUT_PATH}")
    print("Schema types:")
    for schema_type, count in sorted(type_counts.items()):
        print(f"  - {schema_type}: {count}")


if __name__ == "__main__":
    main()
