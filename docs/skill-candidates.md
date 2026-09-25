# Suggested focused skills

Create these only after the corresponding workflow has been implemented and verified. A skill should handle research or planning, then hand a frozen config to the Python controller. It should not inspect every rendered image or control the render loop.

1. **Background cutout planner:** classify subject, pick a researched matting stack, set shadow/reflection policy, and define alpha/geometry QC. Depends on Phase 5 and 6 evidence.
2. **Model comparison:** use official repositories, model cards and licenses; compare at most three candidates against VRAM, quality, speed and compatibility; update registry and research cache with dates and sources.
3. **Commercial license check:** verify the exact model, weights, nodes and dependencies for the intended use, and exclude unclear licenses.
4. **Prompt and workflow planner:** turn a request into task analysis, prompt layers, model selection, parameters, and a frozen job config.
5. **8 GB troubleshooting:** interpret OOM and quality failures, choose documented deterministic retries, and escalate only after retries fail.
6. **Batch intake and QC:** validate files and shared preset once, then summarize script QC exceptions after batch execution.

The first two give the clearest separation of concerns. Do not create background cutout instructions that claim a default model before the benchmark.
