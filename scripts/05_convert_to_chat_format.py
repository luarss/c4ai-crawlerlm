#!/usr/bin/env python3
"""
Convert the dataset to Qwen3 chat format for SFT.

This script converts the HTML-to-JSON dataset into the chat message format
expected by Qwen3 models for fine-tuning.
"""

import json
from pathlib import Path
from tqdm import tqdm

# Paths
TRAIN_INPUT = Path("data/processed/train.jsonl")
TEST_INPUT = Path("data/processed/test.jsonl")
TRAIN_OUTPUT = Path("data/processed/train_chat.jsonl")
TEST_OUTPUT = Path("data/processed/test_chat.jsonl")


def convert_to_chat_format(example: dict) -> dict:
    """
    Convert a single example to Qwen3 chat format.

    Input format:
        {
            "example_html": "<html>...",
            "expected_json": {...}
        }

    Output format:
        {
            "messages": [
                {"role": "user", "content": "Extract structured data..."},
                {"role": "assistant", "content": "{...}"}
            ]
        }
    """
    # Create user prompt
    user_content = f"""Extract structured data from the following HTML and return it as JSON.

HTML:
{example['example_html']}

Return a JSON object with these fields: url, title, text, author, published_date, image, favicon, id"""

    # Create assistant response (JSON string)
    assistant_content = json.dumps(example['expected_json'], ensure_ascii=False, indent=2)

    # Create chat format
    chat_example = {
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
    }

    return chat_example


def convert_file(input_path: Path, output_path: Path):
    """Convert a JSONL file to chat format."""
    print(f"Converting {input_path} → {output_path}")

    examples = []
    with open(input_path) as f:
        for line in f:
            examples.append(json.loads(line))

    print(f"  Loaded {len(examples)} examples")

    # Convert to chat format
    chat_examples = []
    for example in tqdm(examples, desc="  Converting"):
        chat_example = convert_to_chat_format(example)
        chat_examples.append(chat_example)

    # Write output
    with open(output_path, 'w') as f:
        for chat_example in chat_examples:
            f.write(json.dumps(chat_example, ensure_ascii=False) + '\n')

    print(f"  ✓ Wrote {len(chat_examples)} examples to {output_path}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Convert Dataset to Qwen3 Chat Format")
    print("=" * 60)

    # Convert train split
    convert_file(TRAIN_INPUT, TRAIN_OUTPUT)

    # Convert test split
    convert_file(TEST_INPUT, TEST_OUTPUT)

    print("\n✓ Conversion complete!")
    print(f"\nOutput files:")
    print(f"  - {TRAIN_OUTPUT}")
    print(f"  - {TEST_OUTPUT}")

    # Show example
    print("\nExample chat format:")
    with open(TRAIN_OUTPUT) as f:
        example = json.loads(f.readline())
        print(json.dumps(example, indent=2, ensure_ascii=False)[:500] + "...")


if __name__ == "__main__":
    main()
