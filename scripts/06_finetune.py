#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "transformers>=4.40.0",
#     "datasets>=2.18.0",
#     "trl>=0.8.0",
#     "torch>=2.0.0",
#     "peft>=0.10.0",
#     "accelerate>=0.28.0",
#     "bitsandbytes>=0.43.0",
# ]
# ///
"""
Fine-tune Qwen 0.6B on CrawlerLM HTML-to-JSON dataset using SFT.

This script uses HuggingFace TRL for supervised fine-tuning with LoRA adapters.
Designed to run on HuggingFace Jobs infrastructure with T4 GPU.
"""

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import DataCollatorForCompletionOnlyLM, SFTTrainer

MODEL_NAME = "Qwen/Qwen3-0.6B"
DATASET_NAME = "espsluar/crawlerlm-html-to-json"
OUTPUT_DIR = "./results/qwen-crawlerlm-sft"
HF_HUB_MODEL_ID = "espsluar/qwen-crawlerlm-sft"

MAX_SEQ_LENGTH = 8192
BATCH_SIZE = 2
GRADIENT_ACCUMULATION_STEPS = 8
LEARNING_RATE = 2e-5
NUM_EPOCHS = 3
WARMUP_RATIO = 0.1
LOGGING_STEPS = 10
SAVE_STEPS = 100
EVAL_STEPS = 100


def format_chat_template(example, tokenizer):
    """
    Format the dataset examples using the chat template.
    Dataset already has 'messages' field with user/assistant roles.
    """
    formatted = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
    return {"text": formatted}


def main():
    print("=" * 60)
    print("CrawlerLM Fine-tuning Script")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Max sequence length: {MAX_SEQ_LENGTH}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Epochs: {NUM_EPOCHS}")
    print("=" * 60)

    print("\n[1/6] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("\n[2/6] Loading dataset...")
    dataset = load_dataset(DATASET_NAME)
    print(f"  Train examples: {len(dataset['train'])}")
    print(f"  Validation examples: {len(dataset['validation'])}")
    print(f"  Test examples: {len(dataset['test'])}")

    print("\n[3/6] Formatting dataset with chat template...")
    train_dataset = dataset["train"].map(
        lambda x: format_chat_template(x, tokenizer), remove_columns=dataset["train"].column_names
    )
    eval_dataset = dataset["validation"].map(
        lambda x: format_chat_template(x, tokenizer), remove_columns=dataset["validation"].column_names
    )

    print("  Example formatted text (first 500 chars):")
    print(f"  {train_dataset[0]['text'][:500]}...")

    print("\n[4/6] Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    model.gradient_checkpointing_enable()

    response_template = "<|im_start|>assistant"
    collator = DataCollatorForCompletionOnlyLM(response_template=response_template, tokenizer=tokenizer)

    print("\n[5/6] Setting up training arguments...")
    training_args = TrainingArguments(
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
        gradient_checkpointing=True,
        report_to=["tensorboard"],
        hub_model_id=HF_HUB_MODEL_ID,
        push_to_hub=True,
        hub_strategy="every_save",
    )

    print("\n[6/6] Initializing SFT Trainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=collator,
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
    )

    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60 + "\n")

    trainer.train()

    print("\n" + "=" * 60)
    print("Training complete! Saving final model...")
    print("=" * 60)

    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\nPushing to HuggingFace Hub...")
    trainer.push_to_hub()

    print("\n✓ Fine-tuning complete!")
    print(f"  Model saved to: {OUTPUT_DIR}")
    print(f"  Hub model: {HF_HUB_MODEL_ID}")


if __name__ == "__main__":
    main()
