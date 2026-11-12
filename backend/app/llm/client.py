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
    # OpenCode gateway (OpenAI-compatible chat completions). Base URL and model id from its public catalog,
    # https://opencode.ai/zen/v1/models, checked 2026-11-12.
    "opencode": "https://opencode.ai/inference/openai/v1",
}
DEFAULT_MODEL = {  # used when LLM_MODEL is empty
    "opencode": "deepseek-v4.1-flash-free",
    "openrouter": "google/gemma-4-31b-it:free",  # free, 262k context, supports reasoning and response_format (catalog checked 2026-11-12)
}
KEY_PREFIX = {"openrouter": "sk-or-"}  # a key that does not start like this is never sent to that provider (no cross-provider key leaks)
REASONING_CAPABLE = ("opencode", "openrouter")  # models here may think before answering: bigger token budget and timeout


class LLM(Protocol):
    name: str

    def json(self, system: str, user: str, schema: dict) -> Optional[dict]: ...
    def text(self, system: str, user: str) -> Optional[str]: ...


_paused_until: dict = {}  # model name -> unix time before which a rate-limited hosted model is not called again (shared across requests)
_MAX_PAUSE_S = 3600  # re-check at least hourly, whatever Retry-After says

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
    def __init__(self, base: str, model: str, timeout: float = 90):
        self.base, self.model, self.name, self.timeout = base.rstrip("/"), model, f"ollama:{model}", timeout

    def _chat(self, system: str, user: str, fmt=None) -> Optional[str]:
        # Plain text: think=True so Ollama puts the reasoning in message.thinking and the answer alone in message.content. With
        # think=False, qwen3:4b on Ollama 0.13.5 wrote its reasoning into the content (checked 2026-11-12). JSON mode is constrained
        # by the schema, so it stays on think=False and the small budget. Reasoning counts toward num_predict, hence the larger text budget.
        text_mode = fmt is None
        body = {"model": self.model, "stream": False, "think": text_mode, "options": {"temperature": 0, "num_predict": 1000 if text_mode else 400},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": redact(user)}]}
        if fmt:
            body["format"] = fmt
        try:
            r = httpx.post(f"{self.base}/api/chat", json=body, timeout=self.timeout)
            r.raise_for_status()
            return r.json()["message"]["content"] or None  # message.thinking is never used as an answer
        except Exception:  # noqa: BLE001 - any LLM failure falls back to rules
            return None

    def json(self, system, user, schema):
        raw = self._chat(system, user, schema)
        return _loads(raw) if raw else None

    def text(self, system, user):
        raw = self._chat(system, user)
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip() if raw else None


def _describe(r: "httpx.Response", key: str) -> str:
    """Short, key-free reason for a failed call, e.g. 'HTTP 429 FreeUsageLimitError: ...'. Only the status and the gateway's error text."""
    try:
        err = r.json().get("error") or {}
        detail = f"{err.get('type', '')}: {err.get('message', '')}".strip(": ")
        raw = (err.get("metadata") or {}).get("raw")  # OpenRouter puts the upstream provider's reason here
        if isinstance(raw, str) and raw:
            detail += f" ({raw[:140]})"
    except Exception:  # noqa: BLE001 - body was not JSON
        detail = ""
    text = f"HTTP {r.status_code} {detail}".strip()
    return (text.replace(key, "***") if key else text)[:240]


def _retry_wait(r: "httpx.Response") -> int:
    """Seconds until the limit lifts: Retry-After (seconds), else X-RateLimit-Reset (epoch seconds or milliseconds), else one minute."""
    try:
        return int(r.headers["retry-after"])
    except (KeyError, ValueError):
        pass
    try:
        reset = float(r.headers["x-ratelimit-reset"])
        reset = reset / 1000 if reset > 1e11 else reset
        return int(reset - time.time()) if reset > time.time() else 60
    except (KeyError, ValueError):
        return 60


class HostedLLM:
    def __init__(self, provider: str, key: str, model: str, timeout: Optional[float] = None):
        self.base, self.key, self.model, self.name = HOSTED[provider], key, model, f"{provider}:{model}"
        # a reasoning model (the OpenCode DeepSeek one) spends tokens thinking before it answers, so 400 would cut the answer off
        self.max_tokens, self.timeout = (1500, 90) if provider in REASONING_CAPABLE else (400, 60)
        if timeout is not None:  # chat callers pass a short one; scripts/llm_smoke.py keeps the long default
            self.timeout = timeout
        self.last_error: Optional[str] = None  # why the last call returned None; read by scripts/llm_smoke.py

    def _post(self, body: dict) -> "httpx.Response":
        return httpx.post(f"{self.base}/chat/completions", json=body, headers={"Authorization": f"Bearer {self.key}"}, timeout=self.timeout)

    def _chat(self, system: str, user: str, as_json: bool) -> Optional[str]:
        body = {"model": self.model, "temperature": 0, "max_tokens": self.max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": redact(user)}]}
        if as_json:
            body["response_format"] = {"type": "json_object"}
        self.last_error = None
        if time.time() < _paused_until.get(self.name, 0):  # rate-limited a moment ago: skip the call, let the fallback answer
            self.last_error = "paused after a rate limit (see the earlier error)"
            return None
        try:
            r = self._post(body)
            if as_json and r.status_code in (400, 422):  # the gateway refused response_format: ask again without it (the prompt asks for JSON)
                body.pop("response_format")
                r = self._post(body)
            if r.status_code >= 400:
                self.last_error = _describe(r, self.key)
                if r.status_code == 429:
                    _paused_until[self.name] = time.time() + min(max(_retry_wait(r), 60), _MAX_PAUSE_S)
                return None
            content = r.json()["choices"][0]["message"].get("content")
            if not content or not content.strip():  # reasoning-only reply: its reasoning_content is never used as the answer
                self.last_error = "empty answer (no message content)"
                return None
            return content
        except Exception as e:  # noqa: BLE001 - any LLM failure falls back to rules
            self.last_error = type(e).__name__
            return None

    def json(self, system, user, schema):
        raw = self._chat(system + " Reply with one JSON object only.", user, True)
        return _loads(raw) if raw else None

    def text(self, system, user):
        raw = self._chat(system, user, False)
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip() if raw else None


class FallbackLLM:
    """Hosted model first; if it gives no usable answer (error, rate limit, empty), ask the local model instead.
    `name` is whichever model answered last, so the app can show who produced a result."""

    def __init__(self, primary: LLM, secondary: LLM):
        self.primary, self.secondary, self.last_used = primary, secondary, None

    @property
    def name(self) -> str:
        return self.last_used or self.primary.name

    def _ask(self, method: str, *args):
        out = getattr(self.primary, method)(*args)
        if out is not None:
            self.last_used = self.primary.name
            return out
        out = getattr(self.secondary, method)(*args)
        self.last_used = self.secondary.name if out is not None else None
        return out

    def json(self, system, user, schema):
        return self._ask("json", system, user, schema)

    def text(self, system, user):
        return self._ask("text", system, user)


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
    """The model for chat, intake and claim checks: short timeout, the rules answer when it does not reply in time."""
    return build_llm(settings.llm_chat_timeout_s)


def build_llm(timeout: Optional[float] = None) -> Optional[LLM]:
    p = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODEL.get(p, "")
    ok_key = bool(settings.llm_api_key) and settings.llm_api_key.startswith(KEY_PREFIX.get(p, ""))
    hosted = HostedLLM(p, settings.llm_api_key, model, timeout) if p in HOSTED and ok_key and model else None
    wants_local = p in ("auto", "ollama") or (p in HOSTED and settings.llm_local_fallback)  # also when the hosted key is missing or unusable
    local = OllamaLLM(settings.ollama_base_url, settings.ollama_model, timeout or 90) if wants_local and _ollama_up() else None
    if hosted and local:
        return FallbackLLM(hosted, local)
    return hosted or local
