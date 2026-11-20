"""Free LLM access through any OpenAI-compatible endpoint.

Default: GitHub Models (free inside GitHub Actions with the built-in GITHUB_TOKEN),
preferring open-weight models (Llama, Mistral, DeepSeek, Phi).
Override with LLM_BASE_URL / LLM_API_KEY / LLM_MODEL (e.g. Groq or a local Ollama).
"""
from __future__ import annotations

import json
import os
import re

import requests

GITHUB_BASE = "https://models.github.ai/inference"
OPEN_MODEL_PREFERENCE = [
    "llama-3.3-70b", "llama-4-maverick", "llama-4-scout", "deepseek-v3", "mistral-large",
    "mistral-medium", "mistral-small", "phi-4", "llama-3.1-70b", "llama",
]


def _github_open_models(token: str) -> list[str]:
    try:
        r = requests.get("https://models.github.ai/catalog/models",
                         headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        ids = [m["id"] for m in r.json()]
    except Exception as e:  # catalog unavailable -> best-known ids
        print(f"[llm] catalog lookup failed ({e}); using fallback ids")
        ids = ["meta/Llama-3.3-70B-Instruct", "mistral-ai/mistral-small-2503", "microsoft/phi-4"]
    ranked = []
    for pref in OPEN_MODEL_PREFERENCE:
        ranked += [i for i in ids if pref in i.lower() and i not in ranked and "vision" not in i.lower()]
    return ranked[:5] or ids[:3]


def _endpoint() -> tuple[str, str, list[str]]:
    base = os.getenv("LLM_BASE_URL", "").rstrip("/")
    key = os.getenv("LLM_API_KEY", "")
    models = [m.strip() for m in os.getenv("LLM_MODEL", "").split(",") if m.strip()]
    if not base:
        base, key = GITHUB_BASE, key or os.getenv("GITHUB_TOKEN", "")
        if not models and key:
            models = _github_open_models(key)
    return base, key, models


def available() -> bool:
    base, key, models = _endpoint()
    return bool(models) and (bool(key) or "localhost" in base)


def chat(system: str, user: str, temperature: float = 0.6, max_tokens: int = 3000) -> str:
    base, key, models = _endpoint()
    if not models:
        raise RuntimeError("No LLM configured (set GITHUB_TOKEN or LLM_* variables)")
    last = None
    for model in models:
        try:
            r = requests.post(f"{base}/chat/completions", timeout=180,
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                              json={"model": model, "temperature": temperature, "max_tokens": max_tokens,
                                    "messages": [{"role": "system", "content": system},
                                                 {"role": "user", "content": user}]})
            r.raise_for_status()
            print(f"[llm] used {model}")
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            print(f"[llm] {model} failed: {e}")
    raise RuntimeError(f"All models failed: {last}")


def chat_json(system: str, user: str, **kw) -> dict:
    text = chat(system + "\nRespond with ONE valid JSON object only. No markdown fences.", user, **kw)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])
