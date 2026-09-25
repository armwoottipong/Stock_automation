---
name: research-cache
description: Inspect or refresh this project's reviewed model research cache when planning an image workflow. Use for cached model decisions and evidence maintenance, not during the render loop.
---

# Research cache

Work from the repository root. Read `docs/phase-7-results.md` for the entry policy and `AGENTS.md` for model research requirements. Use `python scripts/research_cache.py lookup --task <task> --subject <subject_type>` to inspect a decision without network research. A `fresh` entry can provide a usable model ID only if the current model and license registries still match. A `manual_review` outcome has no automatic model.

For an expired, missing or invalid entry, review official model and license sources and the local benchmark before preparing an update. Read all seven `data/*registry.json` files. Update relevant registry verification dates and prepare a reviewed `ResearchEntry` JSON with a validity window of at most 30 days. Run `python scripts/research_cache.py upsert --entry <file>` only after the evidence is recorded. Do not infer commercial eligibility from the cache alone, and never research within a running render job.
