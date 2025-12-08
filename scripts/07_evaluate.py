import json
import glob
from pathlib import Path
from typing import Dict, Any, Optional

from datasets import load_dataset
from dotenv import load_dotenv
from tqdm import tqdm
import Levenshtein
from rouge_score import rouge_scorer
from llama_cpp import Llama

load_dotenv()


def extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from model response."""
    try:
        # First try to parse the whole response
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON block in the response
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            try:
                return json.loads(text[start_idx:end_idx+1])
            except json.JSONDecodeError:
                pass
    return None


def load_gguf_model(model_path: str, n_ctx: int = 32768, n_gpu_layers: int = 0,
                    base_model_path: Optional[str] = None, lora_path: Optional[str] = None):
    """Load a GGUF model using llama-cpp-python."""
    # If using LoRA adapter mode
    if base_model_path and lora_path:
        print(f"Loading base model from {base_model_path}...")
        print(f"Loading LoRA adapter from {lora_path}...")
        print(f"  Context size: {n_ctx}")
        print(f"  GPU layers: {n_gpu_layers} ({'all' if n_gpu_layers == -1 else 'CPU only' if n_gpu_layers == 0 else n_gpu_layers})")

        model = Llama(
            model_path=base_model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            lora_path=lora_path,
            verbose=False,
        )
        return model

    # Standard mode: single model file
    # If model_path is a directory, find the .gguf file
    if Path(model_path).is_dir():
        gguf_files = glob.glob(str(Path(model_path) / "*.gguf"))
        if not gguf_files:
            raise ValueError(f"No .gguf files found in {model_path}")
        if len(gguf_files) > 1:
            print(f"Warning: Multiple .gguf files found in {model_path}, using {gguf_files[0]}")
        model_path = gguf_files[0]

    print(f"Loading GGUF model from {model_path}...")
    print(f"  Context size: {n_ctx}")
    print(f"  GPU layers: {n_gpu_layers} ({'all' if n_gpu_layers == -1 else 'CPU only' if n_gpu_layers == 0 else n_gpu_layers})")

    model = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        verbose=False,
    )

    return model


def generate_extraction(model: Llama, html: str, max_tokens: int = 1024) -> str:
    """Generate JSON extraction for the given HTML using llama-cpp-python."""
    # Format the prompt
    prompt = f"""Extract structured data from the following HTML and return it as JSON.

HTML:
{html}"""

    print(f"[DEBUG] Prompt length: {len(prompt)} chars")
    print(f"[DEBUG] Starting generation with max_tokens={max_tokens}...")

    # Generate
    output = model(
        prompt,
        max_tokens=max_tokens,
        temperature=0.1,
        top_p=0.95,
        echo=False,  # Don't echo the prompt
        stop=None,
    )

    print(f"[DEBUG] Generation complete")

    # Extract the generated text
    response = output['choices'][0]['text']
    print(f"[DEBUG] Response length: {len(response)} chars")
    return response


def calculate_rouge_l(predicted: str, expected: str) -> float:
    """Calculate ROUGE-L F1 score between predicted and expected text."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(expected, predicted)
    return scores['rougeL'].fmeasure


def calculate_levenshtein_distance(predicted: str, expected: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    return Levenshtein.distance(predicted, expected)


def calculate_normalized_levenshtein(predicted: str, expected: str) -> float:
    """Calculate normalized Levenshtein similarity (0 to 1, higher is better)."""
    max_len = max(len(predicted), len(expected))
    if max_len == 0:
        return 1.0
    distance = Levenshtein.distance(predicted, expected)
    return 1 - (distance / max_len)


def evaluate_model(model_path: str, dataset_name: str, split: str = "test",
                   max_examples: Optional[int] = None, n_ctx: int = 32768,
                   n_gpu_layers: int = 0, base_model_path: Optional[str] = None,
                   lora_path: Optional[str] = None):
    """Evaluate the model on the test set using local GGUF inference."""
    # Load model
    model = load_gguf_model(model_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers,
                           base_model_path=base_model_path, lora_path=lora_path)

    # Load test dataset
    print(f"Loading dataset {dataset_name} (split: {split})...")
    dataset = load_dataset(dataset_name, split=split)

    if max_examples and max_examples > 0:
        dataset = dataset.select(range(min(max_examples, len(dataset))))

    print(f"Evaluating on {len(dataset)} examples...")

    # Metrics
    metrics = {
        "total": len(dataset),
        "valid_json": 0,
        "rouge_l_scores": [],
        "levenshtein_distances": [],
        "normalized_levenshtein_scores": [],
    }

    results = []

    # Evaluate each example
    for idx, example in enumerate(tqdm(dataset, desc="Evaluating")):
        print(f"\n[DEBUG] Processing example {idx}")

        # Extract HTML and expected JSON from messages
        user_content = example["messages"][0]["content"]

        # Extract HTML - handle both "HTML:\n\n" and "HTML:\n" formats
        if "HTML:\n\n" in user_content:
            html = user_content.split("HTML:\n\n", 1)[1]
        elif "HTML:\n" in user_content:
            html = user_content.split("HTML:\n", 1)[1]
        else:
            print(f"\nWarning: Could not find HTML in example {idx}")
            html = user_content

        print(f"[DEBUG] HTML length: {len(html)} chars")

        expected_json = json.loads(example["messages"][1]["content"])

        # Generate prediction
        try:
            response = generate_extraction(model, html)
            predicted_json = extract_json_from_response(response)
        except Exception as e:
            print(f"\nError on example {idx}: {e}")
            import traceback
            traceback.print_exc()
            response = ""
            predicted_json = None

        # Calculate metrics
        is_valid_json = predicted_json is not None
        if is_valid_json:
            metrics["valid_json"] += 1

        # Calculate ROUGE-L and Levenshtein for JSON strings
        pred_str = json.dumps(predicted_json, sort_keys=True) if predicted_json else ""
        exp_str = json.dumps(expected_json, sort_keys=True)

        rouge_l = calculate_rouge_l(pred_str, exp_str)
        lev_distance = calculate_levenshtein_distance(pred_str, exp_str)
        norm_lev = calculate_normalized_levenshtein(pred_str, exp_str)

        metrics["rouge_l_scores"].append(rouge_l)
        metrics["levenshtein_distances"].append(lev_distance)
        metrics["normalized_levenshtein_scores"].append(norm_lev)

        # Store result
        results.append({
            "index": idx,
            "valid_json": is_valid_json,
            "predicted": predicted_json,
            "expected": expected_json,
            "response": response,
            "rouge_l": rouge_l,
            "levenshtein_distance": lev_distance,
            "normalized_levenshtein": norm_lev,
        })

    # Calculate percentages and averages
    metrics["valid_json_pct"] = (metrics["valid_json"] / metrics["total"]) * 100

    # Calculate average ROUGE-L and Levenshtein metrics
    metrics["avg_rouge_l"] = sum(metrics["rouge_l_scores"]) / len(metrics["rouge_l_scores"]) if metrics["rouge_l_scores"] else 0
    metrics["avg_levenshtein_distance"] = sum(metrics["levenshtein_distances"]) / len(metrics["levenshtein_distances"]) if metrics["levenshtein_distances"] else 0
    metrics["avg_normalized_levenshtein"] = sum(metrics["normalized_levenshtein_scores"]) / len(metrics["normalized_levenshtein_scores"]) if metrics["normalized_levenshtein_scores"] else 0

    return metrics, results


def print_metrics(metrics: Dict[str, Any]):
    """Print evaluation metrics."""
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"Total examples: {metrics['total']}")
    print(f"Valid JSON: {metrics['valid_json']} ({metrics['valid_json_pct']:.2f}%)")

    print("\nString Similarity Metrics:")
    print(f"  Average ROUGE-L F1: {metrics['avg_rouge_l']:.4f}")
    print(f"  Average Normalized Levenshtein: {metrics['avg_normalized_levenshtein']:.4f}")
    print(f"  Average Levenshtein Distance: {metrics['avg_levenshtein_distance']:.2f}")
    print("="*60)


def save_results(metrics: Dict[str, Any], results: list, output_file: str = "data/processed/evaluation_results.json"):
    """Save evaluation results to file."""
    output = {
        "metrics": metrics,
        "results": results,
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate GGUF model on test set using llama-cpp-python")
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Path to GGUF model file or directory containing *.gguf files (not used if --base-model and --lora are provided)",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default=None,
        help="Path to base model GGUF file (for LoRA adapter usage)",
    )
    parser.add_argument(
        "--lora",
        type=str,
        default=None,
        help="Path to LoRA adapter GGUF file",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="espsluar/crawlerlm-html-to-json",
        help="Dataset ID on HuggingFace Hub",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split to evaluate on",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Maximum number of examples to evaluate (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/evaluation_results.json",
        help="Output file for results",
    )
    parser.add_argument(
        "--n-ctx",
        type=int,
        default=32768,
        help="Context window size (default: 32768)",
    )
    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=0,
        help="Number of layers to offload to GPU (-1 for all, 0 for CPU only, default: 0)",
    )
    args = parser.parse_args()

    # Validate arguments
    if not (args.model_path or (args.base_model and args.lora)):
        parser.error("Either --model-path or both --base-model and --lora must be provided")

    # Run evaluation
    metrics, results = evaluate_model(
        model_path=args.model_path or "",
        dataset_name=args.dataset,
        split=args.split,
        max_examples=args.max_examples,
        n_ctx=args.n_ctx,
        n_gpu_layers=args.n_gpu_layers,
        base_model_path=args.base_model,
        lora_path=args.lora,
    )

    # Print metrics
    print_metrics(metrics)

    # Save results
    save_results(metrics, results, args.output)
