"""Hosted LLM client, OpenCode provider: request shape, reasoning handling and fail-safe behaviour. HTTP is mocked; no network, no key."""
import copy

import httpx
import pytest

from backend.app.config import settings
from backend.app.llm import client as llm_client
from backend.app.llm.client import HostedLLM, get_llm

URL = "https://opencode.ai/inference/openai/v1/chat/completions"
KEY = "test-key-not-real-123"


def reply(content, status=200, headers=None, **message):
    body = {"choices": [{"message": {"content": content, **message}}]} if status == 200 else content
    return httpx.Response(status, json=body, headers=headers, request=httpx.Request("POST", URL))


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    llm_client._paused_until.clear()  # the rate-limit pause is module-wide; start every test unpaused
    monkeypatch.setattr(settings, "llm_local_fallback", True)
    yield
    llm_client._paused_until.clear()


@pytest.fixture()
def calls(monkeypatch):
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append({"url": url, "json": copy.deepcopy(json), "headers": headers, "timeout": timeout})  # copy: the client edits the body on retry
        return fake_post.queue.pop(0)
    fake_post.queue = []
    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    return sent, fake_post.queue


def make():
    return HostedLLM("opencode", KEY, "deepseek-v4.1-flash-free")


def test_request_goes_to_the_opencode_endpoint_with_a_bearer_key_and_room_to_think(calls):
    sent, queue = calls
    queue.append(reply("4"))
    assert make().text("Be brief.", "What is 2+2?") == "4"
    s = sent[0]
    assert s["url"] == URL and s["headers"] == {"Authorization": f"Bearer {KEY}"} and s["timeout"] == 90
    assert s["json"]["model"] == "deepseek-v4.1-flash-free" and s["json"]["max_tokens"] == 1500 and s["json"]["temperature"] == 0
    assert [m["role"] for m in s["json"]["messages"]] == ["system", "user"]
    assert not {"thinking", "reasoning", "reasoning_effort", "response_format"} & set(s["json"])  # none of these for a plain text call


def test_other_providers_keep_their_small_token_budget(calls):
    sent, queue = calls
    queue.append(reply("ok"))
    HostedLLM("together", KEY, "some/model").text("s", "u")
    assert sent[0]["json"]["max_tokens"] == 400 and sent[0]["timeout"] == 60 and sent[0]["url"].startswith("https://api.together.xyz/")


def test_personal_details_are_removed_before_the_text_leaves(calls):
    sent, queue = calls
    queue.append(reply("ok"))
    make().text("s", "mail me at asha@example.com or call 9876543210")
    sent_text = sent[0]["json"]["messages"][1]["content"]
    assert "asha@example.com" not in sent_text and "9876543210" not in sent_text and "[email]" in sent_text and "[phone]" in sent_text


def test_json_call_parses_an_object_even_after_a_think_block(calls):
    sent, queue = calls
    queue.append(reply('<think>weighing options</think>Here you go: {"tool": "help"}'))
    assert make().json("pick", "u", {}) == {"tool": "help"}
    assert sent[0]["json"]["response_format"] == {"type": "json_object"}
    assert "JSON object only" in sent[0]["json"]["messages"][0]["content"]


def test_json_call_retries_once_without_response_format_if_the_gateway_refuses_it(calls):
    sent, queue = calls
    queue.extend([reply({"error": {"type": "invalid_request_error", "message": "response_format unsupported"}}, status=400), reply('{"a": 1}')])
    assert make().json("s", "u", {}) == {"a": 1}
    assert len(sent) == 2 and "response_format" in sent[0]["json"] and "response_format" not in sent[1]["json"]


def test_reasoning_only_reply_is_not_used_as_an_answer(calls):
    _, queue = calls
    queue.append(reply("", reasoning_content="long chain of thought that must never be shown"))
    llm = make()
    assert llm.text("s", "u") is None and "empty answer" in llm.last_error


def test_free_usage_limit_falls_back_to_none_with_a_key_free_reason(calls):
    _, queue = calls
    queue.append(reply({"type": "error", "error": {"type": "FreeUsageLimitError", "message": f"Free usage limit reached {KEY}"}}, status=429))
    llm = make()
    assert llm.text("s", "u") is None
    assert "429" in llm.last_error and "FreeUsageLimitError" in llm.last_error and KEY not in llm.last_error


def test_network_errors_fall_back_to_none(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectTimeout("slow")
    monkeypatch.setattr(llm_client.httpx, "post", boom)
    llm = make()
    assert llm.text("s", "u") is None and llm.last_error == "ConnectTimeout"


def test_get_llm_uses_the_opencode_default_model_and_needs_a_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "opencode")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(llm_client, "_ollama_up", lambda: False)
    assert get_llm() is None  # no key: rules only, and no local-model probe for an explicit hosted provider
    monkeypatch.setattr(settings, "llm_api_key", KEY)
    llm = get_llm()
    assert isinstance(llm, HostedLLM) and llm.model == "deepseek-v4.1-flash-free" and llm.name == "opencode:deepseek-v4.1-flash-free"
    monkeypatch.setattr(settings, "llm_model", "deepseek-v4.1-flash")
    assert get_llm().model == "deepseek-v4.1-flash"  # an explicit model wins


# ---- local fallback ----
class Fake:
    def __init__(self, name, json_out=None, text_out=None):
        self.name, self.json_out, self.text_out, self.calls = name, json_out, text_out, 0

    def json(self, system, user, schema):
        self.calls += 1
        return self.json_out

    def text(self, system, user):
        self.calls += 1
        return self.text_out


def test_fallback_uses_the_hosted_answer_when_there_is_one():
    hosted, local = Fake("opencode:m", {"a": 1}, "hosted"), Fake("ollama:q", {"a": 2}, "local")
    llm = llm_client.FallbackLLM(hosted, local)
    assert llm.json("s", "u", {}) == {"a": 1} and llm.name == "opencode:m" and local.calls == 0


def test_fallback_asks_the_local_model_when_hosted_gives_nothing():
    hosted, local = Fake("opencode:m"), Fake("ollama:q", {"a": 2}, "local")
    llm = llm_client.FallbackLLM(hosted, local)
    assert llm.text("s", "u") == "local" and llm.name == "ollama:q"
    assert llm.json("s", "u", {}) == {"a": 2} and hosted.calls == 2 and local.calls == 2


def test_fallback_reports_nothing_if_both_fail():
    llm = llm_client.FallbackLLM(Fake("opencode:m"), Fake("ollama:q"))
    assert llm.json("s", "u", {}) is None and llm.text("s", "u") is None and llm.name == "opencode:m"


def test_rate_limit_pauses_the_hosted_model_so_it_is_not_called_again(calls):
    sent, queue = calls
    queue.append(reply({"error": {"type": "FreeUsageLimitError", "message": "limit"}}, status=429, headers={"retry-after": "34255"}))
    llm = make()
    assert llm.text("s", "u") is None and len(sent) == 1
    assert make().text("s", "u") is None and len(sent) == 1  # a new instance (a new request) skips the call
    paused = make()
    assert paused.text("s", "u") is None and "paused" in paused.last_error and len(sent) == 1
    other = HostedLLM("opencode", KEY, "deepseek-v4.1-flash")  # a different model is not paused
    queue.append(reply("ok"))
    assert other.text("s", "u") == "ok" and len(sent) == 2


def test_pause_is_capped_at_an_hour_and_expires(calls):
    sent, queue = calls
    queue.append(reply({"error": {"type": "FreeUsageLimitError", "message": "limit"}}, status=429, headers={"retry-after": "99999"}))
    make().text("s", "u")
    until = llm_client._paused_until["opencode:deepseek-v4.1-flash-free"]
    import time
    assert 3500 < until - time.time() <= 3600
    llm_client._paused_until["opencode:deepseek-v4.1-flash-free"] = time.time() - 1
    queue.append(reply("back"))
    assert make().text("s", "u") == "back"


def test_get_llm_wraps_hosted_with_local_only_when_ollama_is_up_and_allowed(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "opencode")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", KEY)
    monkeypatch.setattr(llm_client, "_ollama_up", lambda: True)
    llm = get_llm()
    assert isinstance(llm, llm_client.FallbackLLM) and llm.primary.name == "opencode:deepseek-v4.1-flash-free" and llm.secondary.name.startswith("ollama:")
    monkeypatch.setattr(settings, "llm_local_fallback", False)
    assert isinstance(get_llm(), HostedLLM)
    monkeypatch.setattr(settings, "llm_local_fallback", True)
    monkeypatch.setattr(llm_client, "_ollama_up", lambda: False)
    assert isinstance(get_llm(), HostedLLM)  # Ollama not running: hosted alone
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(llm_client, "_ollama_up", lambda: True)
    assert isinstance(get_llm(), llm_client.OllamaLLM)  # explicit local choice stays local


# ---- local model request shape ----
def ollama_reply(content, thinking=""):
    return httpx.Response(200, json={"message": {"content": content, "thinking": thinking}}, request=httpx.Request("POST", "http://localhost:11434/api/chat"))


def test_local_text_mode_separates_reasoning_and_returns_only_the_answer(calls):
    sent, queue = calls
    queue.append(ollama_reply("2 plus 2 equals 4.", thinking="Hmm, the user is asking..."))
    out = llm_client.OllamaLLM("http://localhost:11434", "qwen3:4b").text("Be brief.", "mail asha@example.com: what is 2+2?")
    assert out == "2 plus 2 equals 4."
    b = sent[0]["json"]
    assert sent[0]["url"].endswith("/api/chat") and b["think"] is True and b["options"]["num_predict"] == 1000 and "format" not in b
    assert "asha@example.com" not in b["messages"][1]["content"]


def test_local_reasoning_only_reply_is_not_used(calls):
    _, queue = calls
    queue.append(ollama_reply("", thinking="ran out of budget while thinking"))
    assert llm_client.OllamaLLM("http://localhost:11434", "qwen3:4b").text("s", "u") is None


def test_local_json_mode_keeps_schema_and_small_budget(calls):
    sent, queue = calls
    queue.append(ollama_reply('{"tool": "help"}'))
    out = llm_client.OllamaLLM("http://localhost:11434", "qwen3:4b").json("pick", "u", {"type": "object"})
    assert out == {"tool": "help"} and sent[0]["json"]["think"] is False and sent[0]["json"]["options"]["num_predict"] == 400 and sent[0]["json"]["format"] == {"type": "object"}


# ---- OpenRouter ----
OR_KEY = "sk-or-v1-" + "a" * 64
OR_URL = "https://openrouter.ai/api/v1/chat/completions"


def or_llm():
    return HostedLLM("openrouter", OR_KEY, "google/gemma-4-31b-it:free")


def test_openrouter_request_and_answer_ignore_reasoning_fields(calls):
    sent, queue = calls
    queue.append(reply("There are 3 r's.", reasoning="step by step thoughts", reasoning_details=[{"type": "reasoning.text", "text": "..."}]))
    out = or_llm().text("Be brief.", "mail asha@example.com: how many r in strawberry?")
    assert out == "There are 3 r's."  # only message.content; reasoning and reasoning_details are never used
    s = sent[0]
    assert s["url"] == OR_URL and s["headers"] == {"Authorization": f"Bearer {OR_KEY}"}
    assert s["json"]["model"] == "google/gemma-4-31b-it:free" and s["json"]["max_tokens"] == 1500 and s["timeout"] == 90
    assert "reasoning" not in s["json"] and "asha@example.com" not in s["json"]["messages"][1]["content"]


def test_openrouter_reasoning_only_reply_falls_through(calls):
    _, queue = calls
    queue.append(reply(None, reasoning="ran out of tokens while thinking"))
    llm = or_llm()
    assert llm.text("s", "u") is None and "empty answer" in llm.last_error


def test_rate_limit_reset_header_in_epoch_milliseconds_sets_the_pause(calls):
    import time
    _, queue = calls
    reset_ms = int((time.time() + 1200) * 1000)
    queue.append(reply({"error": {"message": "Rate limit exceeded: free-models-per-day", "code": 429}}, status=429, headers={"x-ratelimit-reset": str(reset_ms)}))
    llm = or_llm()
    assert llm.text("s", "u") is None and "429" in llm.last_error and "Rate limit exceeded" in llm.last_error
    assert 1100 < llm_client._paused_until[llm.name] - time.time() <= 1200


def test_get_llm_defaults_the_openrouter_model_and_never_sends_a_foreign_key(monkeypatch):
    monkeypatch.setattr(llm_client, "_ollama_up", lambda: False)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", OR_KEY)
    llm = get_llm()
    assert isinstance(llm, HostedLLM) and llm.model == "google/gemma-4-31b-it:free" and llm.base == "https://openrouter.ai/api/v1"
    monkeypatch.setattr(settings, "llm_api_key", KEY)  # a key that is not in OpenRouter format (for example an OpenCode key)
    assert get_llm() is None


def test_openrouter_with_a_wrong_format_key_still_gets_local_fallback(monkeypatch):
    monkeypatch.setattr(llm_client, "_ollama_up", lambda: True)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "llm_api_key", KEY)
    assert isinstance(get_llm(), llm_client.OllamaLLM)  # the foreign key is dropped, the local model still serves


def test_openrouter_upstream_rate_limit_reason_is_readable_and_the_pause_is_short(calls):
    import time
    _, queue = calls
    queue.append(reply({"error": {"message": "Provider returned error", "code": 429,
                                  "metadata": {"raw": "google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly", "provider_name": "Google AI Studio"}},
                        "user_id": "user_secret_id"}, status=429))
    llm = or_llm()
    assert llm.text("s", "u") is None
    assert "429" in llm.last_error and "temporarily rate-limited upstream" in llm.last_error and "user_secret_id" not in llm.last_error
    assert 50 < llm_client._paused_until[llm.name] - time.time() <= 60  # no Retry-After header: one minute
