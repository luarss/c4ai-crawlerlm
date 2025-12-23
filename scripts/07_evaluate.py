#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "huggingface-hub",
#     "datasets",
#     "transformers",
#     "torch",
#     "accelerate",
#     "rouge-score",
#     "python-Levenshtein",
#     "peft",
# ]
# ///

"""
Evaluation script using Transformers library with GPU acceleration.
Compares base Qwen3-0.6B vs fine-tuned crawlerlm model.

Usage:
    uv run scripts/07_evaluate.py
"""

import json
from pathlib import Path
from typing import Any

import Levenshtein
import torch
from datasets import load_dataset
from peft import PeftModel
from rouge_score import rouge_scorer
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_test_data(
    dataset_name: str = "espsluar/crawlerlm-html-to-json", max_examples: int | None = None
) -> list[dict[str, Any]]:
    """Load test dataset from HuggingFace Hub."""
    print(f"Loading test data from {dataset_name}...")
    ds = load_dataset(dataset_name, split="test")

    examples = []
    for idx, item in enumerate(ds):
        if max_examples is not None and idx >= max_examples:
            break
        examples.append(item)

    print(f"Loaded {len(examples)} test examples")
    return examples


def load_base_model(model_id: str = "Qwen/Qwen3-0.6B"):
    """Load base model with GPU acceleration."""
    print(f"Loading base model: {model_id}")

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    print(f"  Model loaded on: {model.device}")
    return tokenizer, model


def load_finetuned_model(
    base_model_id: str = "Qwen/Qwen3-0.6B",
    adapter_id: str = "espsluar/qwen-crawlerlm-lora",
    revision: str | None = None,
):
    """Load fine-tuned model with LoRA adapter."""
    if revision:
        print(f"Loading fine-tuned model: {base_model_id} + {adapter_id} (revision: {revision})")
    else:
        print(f"Loading fine-tuned model: {base_model_id} + {adapter_id}")

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    model = PeftModel.from_pretrained(base_model, adapter_id, revision=revision)

    print(f"  Model loaded on: {model.device}")
    return tokenizer, model


def run_inference(model, tokenizer, user_prompt: str, max_new_tokens: int = 8192) -> str:
    """Run model inference with user prompt using chat template."""
    messages = [{"role": "user", "content": user_prompt}]

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=8192).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            top_p=0.95,
            do_sample=True,
        )

    generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1] :], skip_special_tokens=True)

    # DEBUG: Print raw generation info
    num_generated_tokens = outputs[0].shape[0] - inputs.input_ids.shape[1]
    print(
        f"  DEBUG: Generated {num_generated_tokens} tokens, {len(generated_text)} chars (before stripping)", flush=True
    )
    if len(generated_text) < 200:
        print(f"  DEBUG: Raw output: {generated_text!r}", flush=True)

    # Post-process: Remove <think> tags and their content if present
    # The model was trained with thinking enabled, so it may generate these tags
    if "<think>" in generated_text:
        # Extract only content after </think>
        parts = generated_text.split("</think>")
        if len(parts) > 1:  # noqa: SIM108
            generated_text = parts[1].strip()
        else:
            # If no closing tag, remove everything from <think> onward
            generated_text = generated_text.split("<think>")[0].strip()

    return generated_text.strip()


def compute_metrics(predictions: list[str], references: list[str]) -> dict[str, float]:
    """Compute ROUGE and Levenshtein metrics."""
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

    rouge1_scores = []
    rouge2_scores = []
    rougeL_scores = []
    levenshtein_distances = []
    normalized_levenshtein = []

    for pred, ref in zip(predictions, references, strict=True):
        scores = scorer.score(ref, pred)
        rouge1_scores.append(scores["rouge1"].fmeasure)
        rouge2_scores.append(scores["rouge2"].fmeasure)
        rougeL_scores.append(scores["rougeL"].fmeasure)

        lev_dist = Levenshtein.distance(pred, ref)
        levenshtein_distances.append(lev_dist)

        max_len = max(len(pred), len(ref))
        normalized_levenshtein.append(1 - (lev_dist / max_len) if max_len > 0 else 1.0)

    return {
        "rouge1": sum(rouge1_scores) / len(rouge1_scores) if rouge1_scores else 0.0,
        "rouge2": sum(rouge2_scores) / len(rouge2_scores) if rouge2_scores else 0.0,
        "rougeL": sum(rougeL_scores) / len(rougeL_scores) if rougeL_scores else 0.0,
        "levenshtein_avg": sum(levenshtein_distances) / len(levenshtein_distances) if levenshtein_distances else 0.0,
        "levenshtein_normalized": sum(normalized_levenshtein) / len(normalized_levenshtein)
        if normalized_levenshtein
        else 0.0,
    }


def evaluate_model(model, tokenizer, test_examples: list[dict[str, Any]], model_name: str) -> dict[str, Any]:
    """Evaluate a model on test examples."""
    predictions = []
    references = []

    print(f"\nEvaluating {model_name}...")
    for idx, example in enumerate(test_examples):
        print(f"[{idx + 1}/{len(test_examples)}] Processing example...", flush=True)

        user_prompt = example["messages"][0]["content"]
        html_start = user_prompt.find("HTML:\n") + 6
        html = user_prompt[html_start:]

        print(f"  HTML length: {len(html)} chars", flush=True)

        reference = example["messages"][1]["content"]

        try:
            print("  Running inference...", flush=True)
            prediction = run_inference(model, tokenizer, user_prompt)
            print(f"  Generated {len(prediction)} chars", flush=True)
            predictions.append(prediction)
        except Exception as e:
            print(f"  Error during inference: {e}", flush=True)
            predictions.append("")

        references.append(reference)

    print("Computing metrics...", flush=True)
    metrics = compute_metrics(predictions, references)

    return {
        "model_name": model_name,
        "metrics": metrics,
        "predictions": predictions,
        "references": references,
    }


def print_comparison_table(base_results: dict, finetuned_results: dict):
    """Print a formatted comparison table."""
    metrics_order = ["rouge1", "rouge2", "rougeL", "levenshtein_normalized", "levenshtein_avg"]
    metric_names = {
        "rouge1": "ROUGE-1 F1",
        "rouge2": "ROUGE-2 F1",
        "rougeL": "ROUGE-L F1",
        "levenshtein_normalized": "Normalized Levenshtein",
        "levenshtein_avg": "Avg Levenshtein Distance",
    }

    col_width_metric = 30
    col_width_value = 15
    metric_header = f"{'Metric':<{col_width_metric}}"
    base_header = f"{'Base Model':<{col_width_value}}"
    ft_header = f"{'Fine-tuned':<{col_width_value}}"
    improvement_header = f"{'Improvement':<{col_width_value}}"
    print(f"\n{metric_header} {base_header} {ft_header} {improvement_header}")
    total_width = col_width_metric + col_width_value * 3
    print("-" * total_width)

    for metric in metrics_order:
        base_val = base_results["metrics"][metric]
        ft_val = finetuned_results["metrics"][metric]

        if metric == "levenshtein_avg":
            improvement = ((base_val - ft_val) / base_val) * 100 if base_val > 0 else 0
            improvement_str = f"{improvement:+.2f}%"
        else:
            improvement = ((ft_val - base_val) / base_val) * 100 if base_val > 0 else 0
            improvement_str = f"{improvement:+.2f}%"

        metric_col = f"{metric_names[metric]:<{col_width_metric}}"
        base_col = f"{base_val:<{col_width_value}.4f}"
        ft_col = f"{ft_val:<{col_width_value}.4f}"
        improvement_col = f"{improvement_str:<{col_width_value}}"
        print(f"{metric_col} {base_col} {ft_col} {improvement_col}")


def main():
    """Main evaluation pipeline."""
    import os

    # Get revision from environment variable or use None for main branch
    revision = os.getenv("ADAPTER_REVISION", None)

    print(f"GPU available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    test_examples = load_test_data(max_examples=5)

    print("Evaluating Base Model")
    print("Loading base model...")
    base_tokenizer, base_model = load_base_model()
    base_results = evaluate_model(base_model, base_tokenizer, test_examples, "Qwen3-0.6B (Base)")

    print("Freeing base model from memory...")
    del base_model
    del base_tokenizer
    torch.cuda.empty_cache()

    print("Evaluating Fine-tuned Model")
    print("Loading fine-tuned model...")
    ft_tokenizer, ft_model = load_finetuned_model(revision=revision)
    model_name = f"CrawlerLM-Qwen3-0.6B ({revision})" if revision else "CrawlerLM-Qwen3-0.6B"
    finetuned_results = evaluate_model(ft_model, ft_tokenizer, test_examples, model_name)

    print("Freeing fine-tuned model from memory...")
    del ft_model
    del ft_tokenizer
    torch.cuda.empty_cache()

    print_comparison_table(base_results, finetuned_results)

    output_dir = Path("eval_results")
    output_dir.mkdir(exist_ok=True, parents=True)

    comparison = {
        "base_model": {
            "name": base_results["model_name"],
            "id": "Qwen/Qwen3-0.6B",
            "metrics": base_results["metrics"],
        },
        "finetuned_model": {
            "name": finetuned_results["model_name"],
            "id": "espsluar/qwen-crawlerlm-lora",
            "revision": revision,
            "metrics": finetuned_results["metrics"],
        },
        "improvements": {},
    }

    for metric in base_results["metrics"]:
        base_val = base_results["metrics"][metric]
        ft_val = finetuned_results["metrics"][metric]

        if metric == "levenshtein_avg":
            improvement = ((base_val - ft_val) / base_val) * 100 if base_val > 0 else 0
        else:
            improvement = ((ft_val - base_val) / base_val) * 100 if base_val > 0 else 0

        comparison["improvements"][metric] = {
            "base": base_val,
            "finetuned": ft_val,
            "improvement_pct": improvement,
        }

    with open(output_dir / "comparison_summary.json", "w") as f:
        json.dump(comparison, f, indent=2)

    samples = []
    for idx in range(len(test_examples)):
        sample = {
            "example_idx": idx,
            "reference": finetuned_results["references"][idx],
            "base_prediction": base_results["predictions"][idx],
            "finetuned_prediction": finetuned_results["predictions"][idx],
        }
        samples.append(sample)

    with open(output_dir / "samples.json", "w") as f:
        json.dump(samples, f, indent=2)

    print(f"SAMPLE OUTPUTS ({len(samples)} examples)")
    for idx, sample in enumerate(samples):
        user_msg = test_examples[idx]["messages"][0]["content"]
        html_start = user_msg.find("HTML:\n") + 6
        html = user_msg[html_start:]

        print(f"\n--- Example {sample['example_idx'] + 1} ---")
        print(f"\n[HTML]:\n{html}")
        print(f"\n[REFERENCE]:\n{sample['reference']}")
        print(f"\n[BASE MODEL]:\n{sample['base_prediction']}")
        print(f"\n[FINE-TUNED]:\n{sample['finetuned_prediction']}")

    print(f"Results saved to {output_dir}/comparison_summary.json")
    print(f"Samples saved to {output_dir}/samples.json")
    print("Evaluation complete!")


if __name__ == "__main__":
    main()
