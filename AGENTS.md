# AGENTS.md

Guidance for coding agents working in this repo:

- Prefer MVP functionality over abstraction.
- Keep the system local-first and offline-friendly.
- Use SQLite until there is a real scaling reason.
- Do not add paid APIs unless explicitly requested.
- Every script must be runnable from the repo root.
- Keep optional integrations behind graceful fallbacks.
- Add clear TODOs for Reddit, external API, and local LLM work.
- After changing pipeline behavior, run `pytest` and `python scripts/run_pipeline.py`.
