#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "transformers>=4.54.0",
#     "datasets>=2.18.0",
#     "trl>=0.8.0",
#     "torch>=2.0.0",
#     "peft>=0.10.0",
#     "accelerate>=0.28.0",
#     "bitsandbytes>=0.43.0",
#     "trackio>=0.1.0",
# ]
# ///
"""
Fine-tune Qwen 0.6B on CrawlerLM HTML-to-JSON dataset using LoRA.

This script uses HuggingFace TRL's battle-tested approach for LoRA fine-tuning.
Designed to run on HuggingFace Jobs infrastructure with T4 GPU.
"""

import os
from datetime import datetime

from datasets import load_dataset
from huggingface_hub import HfApi, create_repo
from peft import LoraConfig
from transformers import AutoTokenizer
from trl import SFTConfig, SFTTrainer

MODEL_NAME = "Qwen/Qwen3-0.6B"
DATASET_NAME = "espsluar/crawlerlm-html-to-json"
OUTPUT_DIR = "./results/qwen-crawlerlm-lora"
HF_HUB_MODEL_ID = "espsluar/qwen-crawlerlm-lora"

MAX_SEQ_LENGTH = 4096
BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 16
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
WARMUP_RATIO = 0.1
LOGGING_STEPS = 1
SAVE_STEPS = 25
EVAL_STEPS = 25


def ensure_branch_exists(repo_id, branch_name):
    """Pre-create branch on HuggingFace Hub to avoid 404 errors."""
    api = HfApi()

    try:
        # Ensure repo exists
        try:
            api.repo_info(repo_id=repo_id, repo_type="model")
        except Exception:
            print(f"Creating repository {repo_id}...")
            create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)

        # Check if branch exists
        refs = api.list_repo_refs(repo_id=repo_id, repo_type="model")
        branches = [ref.name for ref in refs.branches]

        if branch_name in branches:
            print(f"Branch '{branch_name}' already exists")
        else:
            print(f"Creating branch '{branch_name}'...")
            api.create_branch(repo_id=repo_id, branch=branch_name, repo_type="model")
            print(f"Branch '{branch_name}' created successfully")

    except Exception as e:
        print(f"Warning: Could not ensure branch exists: {e}")
        raise


def format_chat_template(example, tokenizer):
    """
    Format the dataset examples using the chat template.
    Dataset already has 'messages' field with user/assistant roles.
    """
    formatted = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
    return {"text": formatted}


def main():
    # Generate unique run name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"qwen-crawlerlm-lora-{timestamp}"

    # Branch name for this run
    branch_name = f"seq{MAX_SEQ_LENGTH}-{timestamp}"

    # Configure Trackio for experiment tracking
    os.environ["TRACKIO_PROJECT_NAME"] = "crawlerlm"
    os.environ["TRACKIO_SPACE_ID"] = "espsluar/trackio"

    print(f"Run name: {run_name}")
    print(f"Hub model ID: {HF_HUB_MODEL_ID}")
    print(f"Branch name: {branch_name}")

    # Pre-create branch to avoid 404 errors during training
    print("\nEnsuring Hub branch exists...")
    ensure_branch_exists(HF_HUB_MODEL_ID, branch_name)
    print(f"Model: {MODEL_NAME}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Max sequence length: {MAX_SEQ_LENGTH}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Epochs: {NUM_EPOCHS}")

    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading dataset...")
    dataset = load_dataset(DATASET_NAME)
    print(f"Train examples: {len(dataset['train'])}")
    print(f"Validation examples: {len(dataset['validation'])}")
    print(f"Test examples: {len(dataset['test'])}")

    print("Formatting dataset with chat template...")
    train_dataset = dataset["train"].map(
        lambda x: format_chat_template(x, tokenizer), remove_columns=dataset["train"].column_names
    )
    eval_dataset = dataset["validation"].map(
        lambda x: format_chat_template(x, tokenizer), remove_columns=dataset["validation"].column_names
    )

    print(f"Example formatted text (first chars): {train_dataset[0]['text'][:500]}...")

    print("Setting up LoRA config with all-linear target modules...")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules="all-linear",
        bias="none",
        task_type="CAUSAL_LM",
    )

    print("Setting up training arguments...")
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        logging_steps=LOGGING_STEPS,
        save_steps=SAVE_STEPS,
        eval_steps=EVAL_STEPS,
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=True,
        optim="paged_adamw_8bit",
        report_to=["trackio"],
        run_name=run_name,
        hub_model_id=HF_HUB_MODEL_ID,
        hub_private_repo=False,
        hub_revision=branch_name,
        push_to_hub=True,
        hub_strategy="every_save",
        dataset_text_field="text",
        max_length=MAX_SEQ_LENGTH,
    )

    print("Initializing SFT Trainer with LoRA (battle-tested approach)...")
    trainer = SFTTrainer(
        model=MODEL_NAME,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        peft_config=peft_config,
        processing_class=tokenizer,
    )

    print("Starting training...")
    trainer.train()

    print("Training complete! Saving LoRA adapters...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\nLoRA fine-tuning complete!")
    print(f"LoRA adapters saved locally to: {OUTPUT_DIR}")
    print(f"Hub model: {HF_HUB_MODEL_ID}")
    print(f"Hub branch: {branch_name}")
    print(f"View at: https://huggingface.co/{HF_HUB_MODEL_ID}/tree/{branch_name}")


if __name__ == "__main__":
    main()
