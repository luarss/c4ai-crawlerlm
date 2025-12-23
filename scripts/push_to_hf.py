"""
Push the CrawlerLM dataset to HuggingFace Hub.

This script uploads the chat-formatted splits to HuggingFace Hub.
"""

import argparse
import json
from pathlib import Path

from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi

TRAIN_CHAT_PATH = Path("data/processed/train_chat.jsonl")
VAL_CHAT_PATH = Path("data/processed/val_chat.jsonl")
TEST_CHAT_PATH = Path("data/processed/test_chat.jsonl")
README_PATH = Path("data/README.md")


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    data = []
    with open(path) as f:
        for line in f:
            data.append(json.loads(line))
    return data


def create_chat_dataset() -> DatasetDict:
    """Create HuggingFace DatasetDict from chat-formatted train/val/test splits."""
    print("Loading chat-formatted train split...")
    train_data = load_jsonl(TRAIN_CHAT_PATH)
    print(f"Loaded {len(train_data)} training examples")

    print("Loading chat-formatted validation split...")
    val_data = load_jsonl(VAL_CHAT_PATH)
    print(f"Loaded {len(val_data)} validation examples")

    print("Loading chat-formatted test split...")
    test_data = load_jsonl(TEST_CHAT_PATH)
    print(f"Loaded {len(test_data)} test examples")

    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    test_dataset = Dataset.from_list(test_data)

    dataset_dict = DatasetDict(
        {
            "train": train_dataset,
            "validation": val_dataset,
            "test": test_dataset,
        }
    )

    return dataset_dict


def push_to_hub(
    dataset_dict: DatasetDict,
    repo_id: str,
    private: bool = False,
):
    """Push dataset to HuggingFace Hub.

    Args:
        dataset_dict: DatasetDict with train/validation/test splits
        repo_id: HuggingFace repository ID
        private: Whether to make the dataset private
    """
    print(f"Pushing dataset to HuggingFace Hub: {repo_id}")
    print(f"Private: {private}")

    dataset_dict.push_to_hub(
        repo_id=repo_id,
        private=private,
    )

    print(f"Dataset successfully pushed to: https://huggingface.co/datasets/{repo_id}")


def upload_readme(repo_id: str):
    """Upload README to HuggingFace dataset."""
    if not README_PATH.exists():
        print(f"README not found at {README_PATH}, skipping upload")
        return

    print(f"Uploading README to {repo_id}...")
    api = HfApi()

    api.upload_file(
        path_or_fileobj=str(README_PATH),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
    )

    print("README uploaded successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Push CrawlerLM dataset to HuggingFace Hub")
    parser.add_argument("repo_id", help="HuggingFace repository ID (format: username/dataset-name)")
    parser.add_argument("--private", action="store_true", help="Make the dataset private")
    parser.add_argument("--skip-readme", action="store_true", help="Skip uploading README file")
    parser.add_argument("--readme-only", action="store_true", help="Upload only README file (skip dataset upload)")
    args = parser.parse_args()

    if "/" not in args.repo_id:
        print("Invalid repository ID. Must be in format: username/dataset-name")
        return

    print(f"Repository: {args.repo_id}")

    if args.readme_only:
        print("Mode: README only")
        try:
            upload_readme(args.repo_id)
            print("README uploaded! View at:")
            print(f"https://huggingface.co/datasets/{args.repo_id}")
        except Exception as e:
            print(f"Error uploading README: {e}")
            print("Make sure you're logged in to HuggingFace:")
            print("  hf auth login")
        return

    print(f"Private: {args.private}")

    dataset_dict = create_chat_dataset()

    print("Dataset structure:")
    print(f"  {dataset_dict}")

    preview_length = 500
    print("Example from train split (first chars):")
    example = dataset_dict["train"][0]
    example_str = str(example)
    print(example_str[:preview_length] + "..." if len(example_str) > preview_length else example_str)

    try:
        push_to_hub(dataset_dict, args.repo_id, args.private)

        if not args.skip_readme:
            upload_readme(args.repo_id)

        print("All done! View your dataset at:")
        print(f"https://huggingface.co/datasets/{args.repo_id}")

    except Exception as e:
        print(f"Error pushing to hub: {e}")
        print("Make sure you're logged in to HuggingFace:")
        print("  hf auth login")
        return


if __name__ == "__main__":
    main()
