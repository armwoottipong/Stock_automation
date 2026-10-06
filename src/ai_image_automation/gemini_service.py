"""Gemini API service for stock quality culling and metadata generation."""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]


def load_gemini_api_key(root: Optional[Path] = None) -> str:
    """Retrieve GEMINI_API_KEY from environment or .env file."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()

    search_root = root or ROOT
    env_file = search_root / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[1].strip().strip('"').strip("'")
                        if key:
                            os.environ["GEMINI_API_KEY"] = key
                            return key

    raise ValueError("GEMINI_API_KEY not found in environment or .env file.")


def call_gemini_api(
    model: str,
    contents: List[Dict[str, Any]],
    generation_config: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    max_retries: int = 4,
    retry_delay_seconds: float = 6.0,
) -> Dict[str, Any]:
    """Execute raw generateContent request against Google Gemini API with rate-limit retries."""
    key = api_key or load_gemini_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    payload: Dict[str, Any] = {"contents": contents}
    if generation_config:
        payload["generationConfig"] = generation_config

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"}
    )

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            last_error = exc
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass

            # Handle 429 (Resource Exhausted / Rate limit) with exponential backoff
            if exc.code == 429:
                sleep_time = retry_delay_seconds * (2 ** (attempt - 1))
                time.sleep(sleep_time)
                continue
            # Handle transient 500 / 503 errors
            elif exc.code in {500, 503}:
                time.sleep(retry_delay_seconds)
                continue
            else:
                raise RuntimeError(f"Gemini API error ({exc.code}): {error_body}") from exc
        except urllib.error.URLError as exc:
            last_error = exc
            time.sleep(retry_delay_seconds)

    raise RuntimeError(f"Gemini API request failed after {max_retries} attempts: {last_error}")


def extract_candidate_text(response: Dict[str, Any]) -> str:
    """Extract response text safely from Gemini response payload."""
    candidates = response.get("candidates", [])
    if not candidates:
        raise ValueError(f"No candidates returned by Gemini: {response}")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError(f"No content parts in candidate: {candidates[0]}")
    return parts[0].get("text", "")


def generate_stock_metadata(
    description: str,
    model: str = "gemini-3.1-flash-lite",
    image_path: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Pre-generate Adobe Stock-compliant Title and Keywords using Gemini API.

    Returns dict with keys: 'title', 'category', 'keywords'.
    """
    prompt = f"""You are a professional stock metadata specialist for Adobe Stock.
Generate commercial-grade metadata for this stock asset:
Subject/Description: "{description}"

Rules for Adobe Stock:
1. Title: 5 to 10 descriptive English words, natural sentence style, capitalizing the first word or Title Case. No clickbait, no spammy repetition, no punctuation except hyphen.
2. Keywords: 25 to 40 relevant, English tags arranged by relevance (most important first).
3. Strictly NO trademark names, NO brand names, NO artist names.
4. Strictly NO forbidden public terms like "AI generated", "generative ai", "render", "photorealistic".
5. For keywords, include descriptive terms for the object, color, shape, usage, concept, and "white background".

Return ONLY valid JSON matching this schema:
{{
  "title": "Descriptive Stock Title",
  "category": 3,
  "keywords": ["tag1", "tag2", "tag3"]
}}
"""
    parts: List[Dict[str, Any]] = [{"text": prompt}]

    if image_path and image_path.is_file():
        mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})

    resp = call_gemini_api(
        model=model,
        contents=[{"parts": parts}],
        generation_config={"responseMimeType": "application/json"},
        api_key=api_key,
    )
    text = extract_candidate_text(resp)
    data = json.loads(text)

    # Sanitize title
    title = str(data.get("title", "")).strip()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"\s+", " ", title).strip()

    # Sanitize keywords
    raw_keywords = data.get("keywords", [])
    keywords: List[str] = []
    seen: set[str] = set()
    for kw in raw_keywords:
        kw_clean = str(kw).strip().lower()
        if not kw_clean or kw_clean in seen or "," in kw_clean:
            continue
        # Exclude AI terms
        if re.search(r"\b(?:ai[ -]?generated|generative ai|artificial intelligence|photorealistic|render)\b", kw_clean):
            continue
        seen.add(kw_clean)
        keywords.append(kw_clean)

    # Ensure white background is present
    if "white background" not in seen and "isolated" in seen:
        keywords.insert(min(5, len(keywords)), "white background")

    return {
        "title": title,
        "category": data.get("category", 3),
        "keywords": keywords[:49],
    }


def inspect_image_candidate(
    image_path: Path,
    description: str = "",
    model: str = "gemini-3.5-flash-lite",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect an image candidate using Gemini Vision based on Adobe Stock acceptance standards.

    Returns dict with keys: 'pass', 'confidence_score', 'defects_detected', 'rejection_reasons', 'summary'.
    """
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = f"""You are a professional stock photography inspector for Adobe Stock.
Inspect this single isolated object candidate based on Adobe Stock acceptance standards:
Subject context: "{description}"

Evaluation criteria:
1. Subject Clarity & Sharpness: Subject must be crisp and in sharp focus. No severe softness, motion blur, or low-resolution artifacts.
2. AI Artifacts & Hallucinations: No anatomical errors, extra limbs, warped geometries, or illogical AI distortions.
3. Clean Isolation: Object must be clearly identifiable and well-isolated on a clean white/solid background.
4. Clean Pixels: No compression banding, noise patches, or dirty halos.
5. Legal & Intellectual Property: Strictly zero visible text, watermarks, brand logos, or trademarked characters.

Return ONLY valid JSON matching this schema:
{{
  "pass": true or false,
  "confidence_score": 0.0 to 1.0,
  "defects_detected": ["list of defects if any"],
  "rejection_reasons": ["reasons why it should be rejected if pass is false"],
  "summary": "concise rationale"
}}
"""
    resp = call_gemini_api(
        model=model,
        contents=[
            {
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime, "data": b64}}
                ]
            }
        ],
        generation_config={"responseMimeType": "application/json"},
        api_key=api_key,
    )
    text = extract_candidate_text(resp)
    return json.loads(text)


def dual_inspect_candidate(
    image_path: Path,
    description: str = "",
    model_primary: str = "gemini-3.1-flash-lite",
    model_secondary: str = "gemini-3.5-flash-lite",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform dual-model inspection on candidate using both Gemini 3.1 and 3.5 Flash Lite.

    Requires consensus (both models pass) to pass the candidate.
    """
    res1 = inspect_image_candidate(image_path, description, model=model_primary, api_key=api_key)
    # Small pause to respect free-tier RPM limits
    time.sleep(2.0)
    res2 = inspect_image_candidate(image_path, description, model=model_secondary, api_key=api_key)

    consensus_pass = bool(res1.get("pass") and res2.get("pass"))
    all_defects = list(dict.fromkeys(res1.get("defects_detected", []) + res2.get("defects_detected", [])))
    all_reasons = list(dict.fromkeys(res1.get("rejection_reasons", []) + res2.get("rejection_reasons", [])))

    return {
        "pass": consensus_pass,
        "primary_model": {
            "model": model_primary,
            "pass": res1.get("pass"),
            "confidence": res1.get("confidence_score"),
            "summary": res1.get("summary"),
        },
        "secondary_model": {
            "model": model_secondary,
            "pass": res2.get("pass"),
            "confidence": res2.get("confidence_score"),
            "summary": res2.get("summary"),
        },
        "defects_detected": all_defects,
        "rejection_reasons": all_reasons,
    }
