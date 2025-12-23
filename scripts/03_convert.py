"""
Convert the dataset to Qwen3 chat format for SFT.

This script converts the dataset into the chat message format with schema-specific prompts.
"""

import json
from pathlib import Path

from qwen_utils import count_chat_tokens
from tqdm import tqdm

TRAIN_INPUT = Path("data/processed/train.jsonl")
VAL_INPUT = Path("data/processed/val.jsonl")
TEST_INPUT = Path("data/processed/test.jsonl")
TRAIN_OUTPUT = Path("data/processed/train_chat.jsonl")
VAL_OUTPUT = Path("data/processed/val_chat.jsonl")
TEST_OUTPUT = Path("data/processed/test_chat.jsonl")

MAX_TOKENS = 24_000

SCHEMA_PROMPTS = {
    "recipe": (
        "Return a JSON object with these fields: type, name, description, author, "
        "prep_time (string), cook_time (string), total_time (string), servings (string), "
        "ingredients (array), instructions (array). "
        "Use flat strings for time fields, not nested objects."
    ),
    "job_posting": (
        "Return a JSON object with these fields: type, title, company, location, "
        "department, employment_type, description. "
        "Use flat strings for all fields."
    ),
    "event": (
        "Return a JSON object with these fields: type, title, datetime (string), location, "
        "venue_name, price (string), organizer, description, event_type. "
        "Use flat strings for datetime and price fields, not nested objects."
    ),
}


def get_schema_prompt(expected_json: dict) -> str:
    """Get schema-specific prompt based on the type field."""
    schema_type = expected_json.get("type", "generic")
    if schema_type not in SCHEMA_PROMPTS:
        valid_types = ", ".join(SCHEMA_PROMPTS.keys())
        raise ValueError(f"Unknown schema type: {schema_type}. Expected one of: {valid_types}")
    return SCHEMA_PROMPTS[schema_type]


def convert_to_chat_format(example: dict) -> dict:
    """
    Convert a single example to chat format with schema-specific prompts.

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
    schema_prompt = get_schema_prompt(example["expected_json"])

    user_content = f"""Extract structured data from the following HTML and return it as JSON.

HTML:
{example["example_html"]}

{schema_prompt}"""

    assistant_content = json.dumps(example["expected_json"], ensure_ascii=False, indent=2)

    chat_example = {
        "messages": [{"role": "user", "content": user_content}, {"role": "assistant", "content": assistant_content}]
    }

    return chat_example


def convert_file(input_path: Path, output_path: Path):
    """Convert a JSONL file to chat format, filtering by token count."""
    print(f"Converting {input_path} → {output_path}")

    examples = []
    with open(input_path) as f:
        for line in f:
            examples.append(json.loads(line))

    print(f"  Loaded {len(examples)} examples")

    chat_examples = []
    filtered_count = 0

    for example in tqdm(examples, desc="  Converting"):
        chat_example = convert_to_chat_format(example)

        # Count tokens in the full conversation using Qwen tokenizer
        total_tokens = count_chat_tokens(chat_example["messages"])

        if total_tokens <= MAX_TOKENS:
            chat_examples.append(chat_example)
        else:
            filtered_count += 1

    with open(output_path, "w") as f:
        for chat_example in chat_examples:
            f.write(json.dumps(chat_example, ensure_ascii=False) + "\n")

    print(f"Wrote {len(chat_examples)} examples to {output_path}")
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} examples exceeding {MAX_TOKENS:,} tokens")


def main():
    """Main entry point."""
    convert_file(TRAIN_INPUT, TRAIN_OUTPUT)
    convert_file(VAL_INPUT, VAL_OUTPUT)
    convert_file(TEST_INPUT, TEST_OUTPUT)

    print("Conversion complete!")
    print("Output files:")
    print(f"  - {TRAIN_OUTPUT}")
    print(f"  - {VAL_OUTPUT}")
    print(f"  - {TEST_OUTPUT}")

    print("Example chat format:")
    with open(TRAIN_OUTPUT) as f:
        example = json.loads(f.readline())
        preview_length = 500
        example_str = json.dumps(example, indent=2, ensure_ascii=False)
        print(example_str[:preview_length] + "..." if len(example_str) > preview_length else example_str)


if __name__ == "__main__":
    main()
