#!/usr/bin/env python3
"""
Common utilities for the CrawlerLM pipeline.
"""

from functools import lru_cache
from transformers import AutoTokenizer


# Qwen3 model to use for tokenization
QWEN_MODEL = "Qwen/Qwen2.5-0.5B"  # Using smallest model for fast tokenizer loading


@lru_cache(maxsize=1)
def get_tokenizer():
    """
    Get the Qwen tokenizer (cached singleton).

    Returns:
        PreTrainedTokenizer: Qwen tokenizer instance
    """
    return AutoTokenizer.from_pretrained(QWEN_MODEL, trust_remote_code=True)


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string using Qwen tokenizer.

    Args:
        text: Input text to tokenize

    Returns:
        int: Number of tokens
    """
    tokenizer = get_tokenizer()
    return len(tokenizer.encode(text))


def count_chat_tokens(messages: list[dict]) -> int:
    """
    Count tokens for a chat format conversation.

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        int: Total number of tokens including chat template overhead
    """
    tokenizer = get_tokenizer()
    # Use apply_chat_template to get accurate token count with special tokens
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )
    return len(tokenizer.encode(text))
