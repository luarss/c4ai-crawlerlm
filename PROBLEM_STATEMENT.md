# Objective
Activate LLM-engineering mindset: dataset thinking, structured outputs, small model fine-tuning, error analysis.

## Task A — Synthetic Dataset Generation
Generate a synthetic dataset for HTML → JSON conversion.

### Requirements:
1. Create 50–100 real HTML examples (messy, inconsistent, nested, partial DOMs).
2. Generate synthetic variations programmatically.
3. Target: 5k examples in the format:

```
<example_html>
<expected_json>
```

4. JSON must follow a stable schema you design.

## Task B – Fine-Tune a Small Model
Use the HuggingFace HF Skills pipeline (example: Qwen 0.6). Here they have shared a detailed lovely article make sure follow this, https://huggingface.co/blog/hf-skills-training

Steps:
1. Run a fine-tuning cycle on your dataset.
2. Test the model on new HTML samples.
3. Compare:
    - baseline performance
    - fine-tuned performance
    - typical failure cases

No need for SOTA accuracy. The goal is:
    - can you complete the pipeline
    - can you reason about the outputs
    - can you tune your dataset for stability

## Task C – Short Findings Summary
1–2 pages describing:
- the dataset characteristics
- model behavior
- what improves after fine-tuning
- what still fails

Focus on clarity over polish.
