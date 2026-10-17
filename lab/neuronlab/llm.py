"""One request to the open-weights model of step 5 (standard library only).

The endpoint is the one OpenCode uses (OPEN_PROTOCOL, OPEN_BASE_URL, OPEN_API_KEY, OPEN_MODEL). Protocol `openai`
(default) speaks <base>/chat/completions: vLLM, SGLang, llama.cpp, Ollama and the vast.ai proxy expose it. Protocol
`anthropic` speaks the Anthropic Messages API, <base>/messages. LLM_PROTOCOL, LLM_BASE_URL, LLM_API_KEY and
LLM_MODEL override the shared values; everything comes from .env.llm.
"""
import json
import os
import urllib.request


def settings():
    protocol = os.environ.get("LLM_PROTOCOL") or os.environ.get("OPEN_PROTOCOL", "openai")
    base = os.environ.get("LLM_BASE_URL") or os.environ.get("OPEN_BASE_URL", "")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPEN_API_KEY", "")
    model = os.environ.get("LLM_MODEL") or os.environ.get("OPEN_MODEL", "")
    if not base or not model or "REPLACE_ME" in f"{base} {key} {model}":
        raise RuntimeError("fill in OPEN_BASE_URL, OPEN_API_KEY and OPEN_MODEL (or LLM_*) in .env.llm")
    return protocol, base.rstrip("/"), key, model


def complete(prompt, system="", max_tokens=None):
    """The model's text answer to one prompt, at temperature 0.

    The default budget is OPEN_MAX_OUTPUT (8192): a reasoning model spends part of it thinking before it answers.
    """
    protocol, base, key, model = settings()
    max_tokens = max_tokens or int(os.environ.get("OPEN_MAX_OUTPUT") or 8192)
    if protocol == "openai":
        url = base + "/chat/completions"
        body = {"model": model, "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    else:
        url = base + "/messages"
        body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "system": system,
                "messages": [{"role": "user", "content": prompt}]}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}", "anthropic-version": "2023-06-01"}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=600) as response:
        answer = json.load(response)
    if protocol == "openai":
        return answer["choices"][0]["message"].get("content") or ""  # null when the budget ended in the thinking
    return "".join(block.get("text", "") for block in answer["content"] if block.get("type") == "text")
