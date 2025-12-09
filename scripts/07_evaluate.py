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
    uv run scripts/09_evaluate_transformers.py
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


def load_test_data(dataset_name: str = "espsluar/crawlerlm-html-to-json", max_examples: int = None) -> list[dict[str, Any]]:
    """Load test dataset from HuggingFace Hub."""
    print(f"Loading test data from {dataset_name}...")
    ds = load_dataset(dataset_name, split="test")

    examples = []
    for idx, item in enumerate(ds):
        if max_examples and idx >= max_examples:
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


def load_finetuned_model(base_model_id: str = "Qwen/Qwen3-0.6B",
                         adapter_id: str = "espsluar/crawlerlm-qwen3-0.6b-test"):
    """Load fine-tuned model with LoRA adapter."""
    print(f"Loading fine-tuned model: {base_model_id} + {adapter_id}")

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    model = PeftModel.from_pretrained(base_model, adapter_id)

    print(f"  Model loaded on: {model.device}")
    return tokenizer, model


def run_inference(model, tokenizer, html: str, max_new_tokens: int = 1024) -> str:
    """Run model inference on HTML input."""
    prompt = f"Extract structured data from the following HTML and return it as JSON.\n\nHTML:\n{html}"

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=8192).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            top_p=0.95,
            do_sample=True,
        )

    # Decode only the generated part (exclude input prompt)
    generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return generated_text.strip()


def compute_metrics(predictions: list[str], references: list[str]) -> dict[str, float]:
    """Compute ROUGE and Levenshtein metrics."""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

    rouge1_scores = []
    rouge2_scores = []
    rougeL_scores = []
    levenshtein_distances = []
    normalized_levenshtein = []

    for pred, ref in zip(predictions, references):
        # ROUGE scores
        scores = scorer.score(ref, pred)
        rouge1_scores.append(scores['rouge1'].fmeasure)
        rouge2_scores.append(scores['rouge2'].fmeasure)
        rougeL_scores.append(scores['rougeL'].fmeasure)

        # Levenshtein distance
        lev_dist = Levenshtein.distance(pred, ref)
        levenshtein_distances.append(lev_dist)

        # Normalized Levenshtein (0-1, where 1 is identical)
        max_len = max(len(pred), len(ref))
        normalized_levenshtein.append(1 - (lev_dist / max_len) if max_len > 0 else 1.0)

    return {
        "rouge1": sum(rouge1_scores) / len(rouge1_scores) if rouge1_scores else 0.0,
        "rouge2": sum(rouge2_scores) / len(rouge2_scores) if rouge2_scores else 0.0,
        "rougeL": sum(rougeL_scores) / len(rougeL_scores) if rougeL_scores else 0.0,
        "levenshtein_avg": sum(levenshtein_distances) / len(levenshtein_distances) if levenshtein_distances else 0.0,
        "levenshtein_normalized": sum(normalized_levenshtein) / len(normalized_levenshtein) if normalized_levenshtein else 0.0,
    }


def evaluate_model(model, tokenizer, test_examples: list[dict[str, Any]], model_name: str) -> dict[str, Any]:
    """Evaluate a model on test examples."""
    predictions = []
    references = []

    print(f"\nEvaluating {model_name}...")
    for idx, example in enumerate(test_examples):
        print(f"[{idx+1}/{len(test_examples)}] Processing example...", flush=True)

        # Extract HTML from user message
        user_msg = example["messages"][0]["content"]
        html_start = user_msg.find("HTML:\n") + 6
        html = user_msg[html_start:]

        print(f"  HTML length: {len(html)} chars", flush=True)

        # Get reference JSON from assistant message
        reference = example["messages"][1]["content"]

        # Run inference
        try:
            print(f"  Running inference...", flush=True)
            prediction = run_inference(model, tokenizer, html)
            print(f"  ✓ Generated {len(prediction)} chars", flush=True)
            predictions.append(prediction)
        except Exception as e:
            print(f"  ✗ Error during inference: {e}", flush=True)
            predictions.append("")

        references.append(reference)

    # Compute metrics
    print(f"Computing metrics...", flush=True)
    metrics = compute_metrics(predictions, references)

    return {
        "model_name": model_name,
        "metrics": metrics,
        "predictions": predictions,
        "references": references,
    }


def print_comparison_table(base_results: dict, finetuned_results: dict):
    """Print a formatted comparison table."""
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS COMPARISON")
    print("=" * 80)

    metrics_order = ["rouge1", "rouge2", "rougeL", "levenshtein_normalized", "levenshtein_avg"]
    metric_names = {
        "rouge1": "ROUGE-1 F1",
        "rouge2": "ROUGE-2 F1",
        "rougeL": "ROUGE-L F1",
        "levenshtein_normalized": "Normalized Levenshtein",
        "levenshtein_avg": "Avg Levenshtein Distance",
    }

    print(f"\n{'Metric':<30} {'Base Model':<15} {'Fine-tuned':<15} {'Improvement':<15}")
    print("-" * 80)

    for metric in metrics_order:
        base_val = base_results['metrics'][metric]
        ft_val = finetuned_results['metrics'][metric]

        if metric == "levenshtein_avg":
            # Lower is better for raw Levenshtein
            improvement = ((base_val - ft_val) / base_val) * 100 if base_val > 0 else 0
            improvement_str = f"{improvement:+.2f}%"
        else:
            # Higher is better for other metrics
            improvement = ((ft_val - base_val) / base_val) * 100 if base_val > 0 else 0
            improvement_str = f"{improvement:+.2f}%"

        print(f"{metric_names[metric]:<30} {base_val:<15.4f} {ft_val:<15.4f} {improvement_str:<15}")

    print("=" * 80)


def main():
    """Main evaluation pipeline."""
    print("=" * 80)
    print("CrawlerLM Model Comparison Evaluation (Transformers)")
    print("=" * 80)

    # Check GPU availability
    print(f"\nGPU available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    # Load test data (limit to 5 for quick test)
    test_examples = load_test_data(max_examples=5)

    # Evaluate base model
    print("\n" + "=" * 80)
    print("PHASE 1: Evaluating Base Model")
    print("=" * 80)

    print("Loading base model...")
    base_tokenizer, base_model = load_base_model()
    base_results = evaluate_model(base_model, base_tokenizer, test_examples, "Qwen3-0.6B (Base)")

    # Free memory
    print("\nFreeing base model from memory...")
    del base_model
    del base_tokenizer
    torch.cuda.empty_cache()

    # Evaluate fine-tuned model
    print("\n" + "=" * 80)
    print("PHASE 2: Evaluating Fine-tuned Model")
    print("=" * 80)

    print("Loading fine-tuned model...")
    ft_tokenizer, ft_model = load_finetuned_model()
    finetuned_results = evaluate_model(ft_model, ft_tokenizer, test_examples, "CrawlerLM-Qwen3-0.6B")

    # Free memory
    print("\nFreeing fine-tuned model from memory...")
    del ft_model
    del ft_tokenizer
    torch.cuda.empty_cache()

    # Print comparison
    print_comparison_table(base_results, finetuned_results)

    # Save detailed results
    output_dir = Path("eval_results")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Save comparison summary
    comparison = {
        "base_model": {
            "name": base_results["model_name"],
            "id": "Qwen/Qwen3-0.6B",
            "metrics": base_results["metrics"],
        },
        "finetuned_model": {
            "name": finetuned_results["model_name"],
            "id": "espsluar/crawlerlm-qwen3-0.6b-test",
            "metrics": finetuned_results["metrics"],
        },
        "improvements": {},
    }

    for metric in base_results["metrics"].keys():
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

    print(f"\n✓ Results saved to {output_dir}/comparison_summary.json")
    print("\nEvaluation complete!")


if __name__ == "__main__":
    main()
