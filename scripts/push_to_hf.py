#!/usr/bin/env python3
"""
Push the CrawlerLM dataset to HuggingFace Hub.

This script uploads the train/test splits to HuggingFace Hub.
"""

import argparse
import json
from pathlib import Path
from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi

# Paths
TRAIN_PATH = Path("data/processed/train.jsonl")
TEST_PATH = Path("data/processed/test.jsonl")
README_PATH = Path("data/README.md")


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    data = []
    with open(path) as f:
        for line in f:
            data.append(json.loads(line))
    return data


def create_dataset() -> DatasetDict:
    """Create HuggingFace DatasetDict from train/test splits."""
    print("Loading train split...")
    train_data = load_jsonl(TRAIN_PATH)
    print(f"  Loaded {len(train_data)} training examples")

    print("Loading test split...")
    test_data = load_jsonl(TEST_PATH)
    print(f"  Loaded {len(test_data)} test examples")

    # Create datasets
    train_dataset = Dataset.from_list(train_data)
    test_dataset = Dataset.from_list(test_data)

    # Create DatasetDict
    dataset_dict = DatasetDict({
        "train": train_dataset,
        "test": test_dataset,
    })

    return dataset_dict


def push_to_hub(dataset_dict: DatasetDict, repo_id: str, private: bool = False):
    """Push dataset to HuggingFace Hub."""
    print(f"\nPushing dataset to HuggingFace Hub: {repo_id}")
    print(f"  Private: {private}")

    dataset_dict.push_to_hub(
        repo_id=repo_id,
        private=private,
    )

    print(f"\n✓ Dataset successfully pushed to: https://huggingface.co/datasets/{repo_id}")


def upload_readme(repo_id: str):
    """Upload README to HuggingFace dataset."""
    if not README_PATH.exists():
        print(f"\n⚠ README not found at {README_PATH}, skipping upload")
        return

    print(f"\nUploading README to {repo_id}...")
    api = HfApi()

    api.upload_file(
        path_or_fileobj=str(README_PATH),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
    )

    print(f"✓ README uploaded successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Push CrawlerLM dataset to HuggingFace Hub"
    )
    parser.add_argument(
        "repo_id",
        help="HuggingFace repository ID (format: username/dataset-name)"
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make the dataset private"
    )
    parser.add_argument(
        "--skip-readme",
        action="store_true",
        help="Skip uploading README file"
    )
    parser.add_argument(
        "--readme-only",
        action="store_true",
        help="Upload only README file (skip dataset upload)"
    )
    args = parser.parse_args()

    # Validate repository ID
    if "/" not in args.repo_id:
        print("❌ Invalid repository ID. Must be in format: username/dataset-name")
        return

    print("=" * 60)
    print("CrawlerLM Dataset → HuggingFace Hub")
    print("=" * 60)
    print(f"\nRepository: {args.repo_id}")

    # README-only mode
    if args.readme_only:
        print("Mode: README only")
        try:
            upload_readme(args.repo_id)
            print(f"\n🎉 README uploaded! View at:")
            print(f"   https://huggingface.co/datasets/{args.repo_id}")
        except Exception as e:
            print(f"\n❌ Error uploading README: {e}")
            print("\nMake sure you're logged in to HuggingFace:")
            print("  hf auth login")
        return

    # Full dataset upload mode
    print(f"Private: {args.private}")

    # Create dataset
    dataset_dict = create_dataset()

    # Show dataset info
    print("\nDataset structure:")
    print(dataset_dict)

    # Push to hub
    try:
        push_to_hub(dataset_dict, args.repo_id, args.private)

        # Upload README unless skipped
        if not args.skip_readme:
            upload_readme(args.repo_id)

        print(f"\n🎉 All done! View your dataset at:")
        print(f"   https://huggingface.co/datasets/{args.repo_id}")

    except Exception as e:
        print(f"\n❌ Error pushing to hub: {e}")
        print("\nMake sure you're logged in to HuggingFace:")
        print("  hf auth login")
        return


if __name__ == "__main__":
    main()
