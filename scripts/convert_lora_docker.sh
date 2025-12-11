#!/bin/bash
# Script to convert LoRA adapter to GGUF format and upload to Hugging Face
# Usage: ./convert_lora_docker.sh <hf_repo_id> <base_model_dir> <lora_model_dir>
# Example: ./convert_lora_docker.sh espsluar/crawlerlm-qwen3-0.6b-test qwen3-0.6b-base crawlerlm-qwen3-0.6b-test

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <hf_repo_id> <base_model_dir> <lora_model_dir>"
    echo ""
    echo "Arguments:"
    echo "  hf_repo_id      - Hugging Face repository ID (e.g., espsluar/model-name)"
    echo "  base_model_dir  - Directory name of base model in ~/workspace/llama.cpp/models/"
    echo "  lora_model_dir  - Directory name of LoRA adapter in ~/workspace/llama.cpp/models/"
    echo ""
    echo "Example:"
    echo "  $0 espsluar/crawlerlm-qwen3-0.6b-test qwen3-0.6b-base crawlerlm-qwen3-0.6b-test"
    exit 1
fi

HF_REPO_ID="$1"
BASE_MODEL_DIR="$2"
LORA_MODEL_DIR="$3"
LLAMA_CPP_DIR="$HOME/workspace/llama.cpp"
OUTPUT_FILE="adapter-lora-q8_0.gguf"

echo "=== LoRA to GGUF Conversion & Upload ==="
echo "HF Repository: $HF_REPO_ID"
echo "Base Model: $BASE_MODEL_DIR"
echo "LoRA Adapter: $LORA_MODEL_DIR"
echo "Output File: $OUTPUT_FILE"
echo ""

# Check if directories exist
if [ ! -d "$LLAMA_CPP_DIR/models/$BASE_MODEL_DIR" ]; then
    echo "Error: Base model directory not found: $LLAMA_CPP_DIR/models/$BASE_MODEL_DIR"
    exit 1
fi

if [ ! -d "$LLAMA_CPP_DIR/models/$LORA_MODEL_DIR" ]; then
    echo "Error: LoRA model directory not found: $LLAMA_CPP_DIR/models/$LORA_MODEL_DIR"
    exit 1
fi

# Step 1: Convert LoRA to GGUF using Docker
echo "Step 1/2: Converting LoRA to GGUF format (Q8_0)..."
docker run --rm \
    -v "$LLAMA_CPP_DIR:/workspace" \
    -w /workspace \
    --entrypoint /bin/bash \
    ghcr.io/ggml-org/llama.cpp:full \
    -c "python3 convert_lora_to_gguf.py \
      models/$LORA_MODEL_DIR \
      --base models/$BASE_MODEL_DIR \
      --outfile models/$LORA_MODEL_DIR/$OUTPUT_FILE \
      --outtype q8_0"

if [ ! -f "$LLAMA_CPP_DIR/models/$LORA_MODEL_DIR/$OUTPUT_FILE" ]; then
    echo "Error: GGUF file was not created"
    exit 1
fi

echo ""
echo "Conversion complete! GGUF file size:"
ls -lh "$LLAMA_CPP_DIR/models/$LORA_MODEL_DIR/$OUTPUT_FILE" | awk '{print $5, $9}'
echo ""

# Step 2: Upload to Hugging Face
echo "Step 2/2: Uploading to Hugging Face Hub..."
cd "$LLAMA_CPP_DIR/models/$LORA_MODEL_DIR"
hf upload "$HF_REPO_ID" "$OUTPUT_FILE" "$OUTPUT_FILE"

echo ""
echo "=== Upload Complete ==="
echo "GGUF file available at:"
echo "https://huggingface.co/$HF_REPO_ID/blob/main/$OUTPUT_FILE"
