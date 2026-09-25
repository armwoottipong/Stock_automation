# Using this project with another coding agent

The image pipeline is a local Python CLI and ComfyUI API workflow. It does not call a particular coding agent in the render loop. A coding agent can edit the repository, run tests and invoke `controller.py` if it has filesystem and terminal access to the checkout.

## Google Antigravity

Google's [Antigravity project documentation](https://antigravity.google/docs/projects?tab=cli) describes adding a local folder or Git repository as a project and using an isolated worktree for concurrent agents. Its [IDE overview](https://www.antigravity.google/docs/ide/overview/) says agents can use the editor and terminal. Add `D:\Stock_automation` as a project folder and tell the agent to read `AGENTS.md`, `README.md`, and `docs/implementation-plan.md` before changes.

Suggested first prompt:

> Work in `D:\Stock_automation`. Read `AGENTS.md`, `README.md`, and `docs/implementation-plan.md`. Keep the phase gates, model registry, license checks and 8 GB VRAM constraints. Run `python -m pytest -q` after code changes. Use a separate Git worktree or coordinate before editing files another agent is editing. Do not download a new model until its source, license and install plan are recorded and I have approved that specific download.

The local `.venv-comfyui`, `vendor/ComfyUI`, model weights, `jobs/` and generated images are ignored by Git. A fresh clone or isolated worktree therefore has source code but not the runtime or weights. For GPU smoke tests, use the configured `D:\Stock_automation` checkout with its installed runtime, or set up the runtime in the other checkout. Keep a single ComfyUI server on port 8188 and avoid simultaneous GPU jobs on the 8 GB card.

Other agents can follow the same approach: open or clone the GitHub repository, install the Python package, read project instructions, and use the CLI. They do not need Codex-specific APIs for image execution.
