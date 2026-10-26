# model

Configuration only — no weights, no notebooks, no keys.

- `model.config.json` — per-provider kind, model name, first-token timeout, request timeout and
  max-token cap. The runtime reads defaults from `app/config.py`; this file documents the intended
  shape for anyone swapping models.
- `setup_local.ps1` — optional helper for a local Ollama install.
- `.env.model.example` — the variable names for a local model endpoint, all values blank.

The paid droplet gateway and the Kaggle notebooks were removed (knowledge.md Amendment C.24). The
supported providers are `gemini`, `groq`, `ollama` (local) and `mock`; production uses
`gemini,groq,mock`.

Never commit `.env.model`. It is git-ignored.
