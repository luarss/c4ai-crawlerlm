"""
Common utilities for the CrawlerLM pipeline.
"""

from functools import lru_cache

from transformers import AutoTokenizer

QWEN_MODEL = "Qwen/Qwen2.5-0.5B"


@lru_cache(maxsize=1)
def get_tokenizer():
    """Get the Qwen tokenizer (cached singleton)."""
    return AutoTokenizer.from_pretrained(QWEN_MODEL, trust_remote_code=True)


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string using Qwen tokenizer."""
    tokenizer = get_tokenizer()
    return len(tokenizer.encode(text))


def count_chat_tokens(messages: list[dict]) -> int:
    """Count tokens for a chat format conversation."""
    tokenizer = get_tokenizer()
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return len(tokenizer.encode(text))
