---
description: Universal policy guardrails for Adobe Stock Generative AI generation, visual QC, and metadata
trigger: always_on
---

# Adobe Stock Contributor Policy Guardrails (2026-10-06)

Reference: `docs/adobe-stock-specification.md`

## 1. P0 Pre-Generation Blocking (Legal & IP Gate)
Before creating any image or accepting a prompt:
- **BLOCK**: Any artist names, pseudonyms, or phrases like "in the style of", "inspired by", "in the tradition of", "drawing on".
- **BLOCK**: Known real public figures, celebrities, or identifiable persons without valid signed model releases.
- **BLOCK**: Fictional characters from games, anime, cartoons, movies, books, or franchises.
- **BLOCK**: Creative works, copyrighted architecture, and trademarked product designs/distinctive packaging.
- **BLOCK**: Government agencies or official law-enforcement emblems.
- **BLOCK**: Real news simulation, disaster footage, or editorial claims ("breaking news", "photo from [real disaster]").
- **BLOCK**: Third-party IP, brand names, logos, or registered trademarks.

## 2. Technical Baseline (ADS-IMG-001 to 004)
- **Format**: JPEG with sRGB color profile.
- **Resolution**: 4–100 Megapixels.
- **File Size**: <= 45 MB.
- **Cleanliness**: Absolutely zero watermarks, signatures, timestamps, borders, or branding.

## 3. Anti-Spam & Similarity (ADS-DUP-001, ADS-DUP-002)
- Do NOT generate superficial variations (flip, rotate, color filter, simple crop, minor color shifts).
- Limit similar concept submissions to a maximum of 2–3 iterations with distinct actions, settings, or compositions.

## 4. Metadata Strict Invariants (ADS-META-001 to 007)
- **Title**: Natural English sentence, descriptive, <= 70 characters, no commas, no brand/AI buzzwords.
- **Keywords**: 5 to 49 keywords, ordered strictly from most important core subject (1-5) to context (6-12), concept (13-20), attributes (21-30), and composition (31-40). Single language only.
- **Category**: Must match one of the 21 official Adobe Stock categories.
- **JPEG Invariant**: Never include "transparent" or "transparency" tags on JPEG assets.
