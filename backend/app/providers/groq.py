"""Groq backup provider.

Groq exposes an OpenAI-compatible chat-completions API:
  base URL  https://api.groq.com/openai/v1
  path      /chat/completions
  auth      Authorization: Bearer $GROQ_API_KEY
  docs      https://console.groq.com/docs/overview  and  /docs/models

Default model `openai/gpt-oss-20b` (1000 t/s, 131k context) is overridable with GROQ_MODEL.
The extraction call is not streamed: the app's provider interface is request/response and the
whole object has to validate before it is written to the spec. A 429 is retried with the
server's `retry-after` (then 2 s) before the chain moves on to the next provider.
"""
from app.config import settings
from app.providers.base import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    name = "groq"

    def __init__(self, config=None) -> None:
        # The chain passes its own Settings instance so tests can swap one object and so the
        # provider and the chain can never read different configuration.
        conf = config or settings
        super().__init__(
            "groq",
            conf.groq_base_url,
            conf.groq_model,
            conf.groq_api_key,
            auth="bearer",
            max_tokens=900,
            timeout=60.0,
            transcript_chars=24000,
            rate_limit_retries=2,
        )
