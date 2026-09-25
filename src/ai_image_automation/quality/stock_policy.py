"""Prompt guardrails and explicit human review requirements for stock imagery."""

STOCK_NEGATIVE_PROMPT = (
    "text, lettering, numbers, typography, logo, brand mark, trademark, "
    "watermark, signature, product label"
)
STOCK_REVIEW_CHECKS = ("visible_text", "logo", "branding")


def with_stock_negative_prompt(extra: str) -> str:
    extra = extra.strip()
    return f"{extra}, {STOCK_NEGATIVE_PROMPT}" if extra else STOCK_NEGATIVE_PROMPT
