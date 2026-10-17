"""One request to the open-weights model of step 5 (standard library only).

Protocol `anthropic` (default) speaks the Anthropic Messages API of the same endpoint Claude Code uses
(ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, OPEN_MODEL): Ollama, llama.cpp, vLLM and hosted services expose it.
Protocol `openai` speaks /v1/chat/completions for endpoints that only have that one. LLM_BASE_URL, LLM_API_KEY
and LLM_MODEL override the shared values; everything comes from .env.llm.
"""
import json
import os
import urllib.request


def settings():
    protocol = os.environ.get("LLM_PROTOCOL", "anthropic")
    base = os.environ.get("LLM_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL", "")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    model = os.environ.get("LLM_MODEL") or os.environ.get("OPEN_MODEL", "")
    if not base or not model or "REPLACE_ME" in f"{base} {key} {model}":
        raise RuntimeError("fill in ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN and OPEN_MODEL (or LLM_*) in .env.llm")
    return protocol, base.rstrip("/"), key, model


def complete(prompt, system="", max_tokens=2048):
    """The model's text answer to one prompt, at temperature 0."""
    protocol, base, key, model = settings()
    if protocol == "openai":
        url = base + "/chat/completions"
        body = {"model": model, "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    else:
        url = base + "/v1/messages"
        body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "system": system,
                "messages": [{"role": "user", "content": prompt}]}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}", "anthropic-version": "2023-06-01"}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=600) as response:
        answer = json.load(response)
    if protocol == "openai":
        return answer["choices"][0]["message"]["content"]
    return "".join(block.get("text", "") for block in answer["content"] if block.get("type") == "text")
