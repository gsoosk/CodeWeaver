"""Azure AI Foundry backend.

Foundry exposes two endpoint shapes and they need different clients:

  * **Azure OpenAI**   `https://<resource>.openai.azure.com`
    -> `openai.AzureOpenAI`, addressed by DEPLOYMENT name, needs `api_version`.
  * **Foundry Models** `https://<resource>.services.ai.azure.com/models`
    -> OpenAI-compatible; `openai.OpenAI` with `base_url` works, addressed by
       MODEL name.

We auto-detect from the endpoint host so the caller only has to supply endpoint,
key and model.

Configuration (flags win over environment):

    AZURE_AI_ENDPOINT     required, e.g. https://my-res.services.ai.azure.com/models
    AZURE_AI_API_KEY      required
    AZURE_AI_MODEL        model or deployment name
    AZURE_AI_API_VERSION  Azure-OpenAI only (default 2024-10-21)

Install: `pip install openai`
"""
from __future__ import annotations

import os
import time

from .base import Completion, Usage


class FoundryBackend:
    name = "foundry"

    def __init__(
        self,
        model: str | None = None,
        endpoint: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 32000,
        timeout: float = 1800.0,
        max_retries: int = 4,
    ):
        try:
            import openai  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("the foundry backend needs the openai package: pip install openai") from exc

        self.endpoint = (endpoint or os.environ.get("AZURE_AI_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("AZURE_AI_API_KEY", "")
        self.model = model or os.environ.get("AZURE_AI_MODEL", "")
        self.api_version = api_version or os.environ.get("AZURE_AI_API_VERSION", "2024-10-21")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

        missing = [n for n, v in
                   (("AZURE_AI_ENDPOINT", self.endpoint),
                    ("AZURE_AI_API_KEY", self.api_key),
                    ("AZURE_AI_MODEL", self.model)) if not v]
        if missing:
            raise SystemExit(f"foundry backend missing config: {', '.join(missing)}")

        self._client = self._build_client()

    def _build_client(self):
        import openai
        if "openai.azure.com" in self.endpoint:
            # Deployment-addressed Azure OpenAI.
            return openai.AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        # Foundry Models (OpenAI-compatible). The path must end in /models.
        base = self.endpoint if self.endpoint.endswith("/models") else f"{self.endpoint}/models"
        return openai.OpenAI(
            base_url=base,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def complete(self, system: str, user: str) -> Completion:
        t0 = time.monotonic()
        kwargs = dict(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=self.temperature,
        )
        try:
            resp = self._client.chat.completions.create(max_tokens=self.max_tokens, **kwargs)
        except Exception as exc:
            # Reasoning models reject `max_tokens` and/or a non-default temperature.
            msg = str(exc)
            if "max_tokens" in msg or "max_completion_tokens" in msg:
                kwargs.pop("temperature", None)
                resp = self._client.chat.completions.create(
                    max_completion_tokens=self.max_tokens, **kwargs)
            elif "temperature" in msg:
                kwargs.pop("temperature", None)
                resp = self._client.chat.completions.create(max_tokens=self.max_tokens, **kwargs)
            else:
                raise
        elapsed = time.monotonic() - t0

        u = getattr(resp, "usage", None)
        usage = Usage(
            prompt_tokens=getattr(u, "prompt_tokens", None),
            completion_tokens=getattr(u, "completion_tokens", None),
            total_tokens=getattr(u, "total_tokens", None),
            wall_clock_s=round(elapsed, 2),
        )
        text = (resp.choices[0].message.content or "") if resp.choices else ""
        return Completion(text=text, usage=usage, model=self.model)
