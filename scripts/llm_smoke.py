"""Check the configured hosted LLM end to end with one tiny text call and one JSON call.

Reads LLM_PROVIDER, LLM_API_KEY and LLM_MODEL from .env (see .env.example). Prints which provider and model it used, whether
each call worked, how long it took, and on failure the HTTP status and the gateway's error text. The key is never printed.
Usage: .venv/bin/python scripts/llm_smoke.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.config import settings  # noqa: E402
from backend.app.llm.client import KEY_PREFIX, HostedLLM, build_llm  # noqa: E402


def main() -> int:
    print(f"provider={settings.llm_provider} model={settings.llm_model or '(provider default)'} key={'set' if settings.llm_api_key else 'NOT SET'}")
    llm = build_llm()  # no short timeout: a reasoning model may need its full time
    if llm is None:
        print("No LLM configured: set LLM_PROVIDER, LLM_API_KEY (and LLM_MODEL) in .env. The app still works on its rules.")
        prefix = KEY_PREFIX.get(settings.llm_provider)
        if prefix and settings.llm_api_key and not settings.llm_api_key.startswith(prefix):
            print(f"  LLM_API_KEY does not start with '{prefix}', so it was not sent to {settings.llm_provider} (it may belong to another provider).")
        return 1
    hosted = getattr(llm, "primary", llm)  # with local fallback on, `llm` wraps the hosted model and Ollama
    print(f"using {llm.name}" + (f" (falls back to {llm.secondary.name})" if hasattr(llm, "secondary") else ""))
    ok = True
    t = time.time()
    out = llm.text("Answer in one short sentence.", "What is 2 plus 2?")
    print(f"text call: {'OK' if out else 'FAILED'} in {time.time() - t:.1f}s, answered by {llm.name}" + (f" -> {out[:120]!r}" if out else ""))
    if isinstance(hosted, HostedLLM) and hosted.last_error:
        print(f"  hosted model: {hosted.last_error}")
    ok &= bool(out)
    t = time.time()
    js = llm.json("Return the tool name.", 'Pick "help" as the tool.', {"type": "object", "properties": {"tool": {"type": "string"}}})
    print(f"json call: {'OK' if js else 'FAILED'} in {time.time() - t:.1f}s, answered by {llm.name}" + (f" -> {js}" if js else ""))
    if isinstance(hosted, HostedLLM) and hosted.last_error:
        print(f"  hosted model: {hosted.last_error}")
    ok &= bool(js)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
