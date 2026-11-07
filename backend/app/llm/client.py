"""Small-model LLM access (Qwen3-4B class). The LLM only parses text, picks a tool and phrases answers (D-07):
it never produces numbers shown to users. Every call is optional; None means 'use the rule-based path'."""
import json
import re
import time
from typing import Optional, Protocol

import httpx

from ..config import settings

HOSTED = {
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "dashscope": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "hf": "https://router.huggingface.co/v1",
}


class LLM(Protocol):
    name: str

    def json(self, system: str, user: str, schema: dict) -> Optional[dict]: ...
    def text(self, system: str, user: str) -> Optional[str]: ...


_PII = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email]"), (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"), "[phone]")]


def redact(text: str) -> str:
    """NFR-02: strip emails and phone numbers before any text leaves the server."""
    for rx, rep in _PII:
        text = rx.sub(rep, text)
    return text


def _loads(raw: str) -> Optional[dict]:
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


class OllamaLLM:
    def __init__(self, base: str, model: str):
        self.base, self.model, self.name = base.rstrip("/"), model, f"ollama:{model}"

    def _chat(self, system: str, user: str, fmt=None) -> Optional[str]:
        body = {"model": self.model, "stream": False, "think": False, "options": {"temperature": 0, "num_predict": 400},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": redact(user)}]}
        if fmt:
            body["format"] = fmt
        try:
            r = httpx.post(f"{self.base}/api/chat", json=body, timeout=90)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception:  # noqa: BLE001 - any LLM failure falls back to rules
            return None

    def json(self, system, user, schema):
        raw = self._chat(system, user, schema)
        return _loads(raw) if raw else None

    def text(self, system, user):
        raw = self._chat(system, user)
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip() if raw else None


class HostedLLM:
    def __init__(self, provider: str, key: str, model: str):
        self.base, self.key, self.model, self.name = HOSTED[provider], key, model, f"{provider}:{model}"

    def _chat(self, system: str, user: str, as_json: bool) -> Optional[str]:
        body = {"model": self.model, "temperature": 0, "max_tokens": 400,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": redact(user)}]}
        if as_json:
            body["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(f"{self.base}/chat/completions", json=body, headers={"Authorization": f"Bearer {self.key}"}, timeout=60)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001
            return None

    def json(self, system, user, schema):
        raw = self._chat(system + " Reply with one JSON object only.", user, True)
        return _loads(raw) if raw else None

    def text(self, system, user):
        raw = self._chat(system, user, False)
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip() if raw else None


_probe = {"t": 0.0, "ok": False}


def _ollama_up() -> bool:
    if time.time() - _probe["t"] > 30:
        try:
            _probe["ok"] = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=0.7).status_code == 200
        except Exception:  # noqa: BLE001
            _probe["ok"] = False
        _probe["t"] = time.time()
    return _probe["ok"]


def get_llm() -> Optional[LLM]:
    p = settings.llm_provider
    if p in HOSTED and settings.llm_api_key and settings.llm_model:
        return HostedLLM(p, settings.llm_api_key, settings.llm_model)
    if p in ("auto", "ollama") and _ollama_up():
        return OllamaLLM(settings.ollama_base_url, settings.ollama_model)
    return None
