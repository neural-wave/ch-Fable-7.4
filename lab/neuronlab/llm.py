"""One request to the language model of step 5 (standard library only): Claude Code, or an open-weights endpoint.

LLM_BACKEND picks the backend (in .env.llm or the environment):
- `claude` (default): `claude -p` answers one prompt headless: no tools, no skills, no MCP servers, no saved
  session, and the system prompt of the caller instead of the one of Claude Code. It uses the login of the `claude`
  CLI (subscription or ANTHROPIC_API_KEY). LLM_MODEL picks the model, e.g. `opus`; without it Claude Code uses its
  default model.
- `open`: the endpoint OpenCode uses (OPEN_PROTOCOL, OPEN_BASE_URL, OPEN_API_KEY, OPEN_MODEL; LLM_PROTOCOL,
  LLM_BASE_URL, LLM_API_KEY and LLM_MODEL override them). Protocol `openai` (default) speaks <base>/chat/completions:
  vLLM, SGLang, llama.cpp, Ollama and the vast.ai proxy expose it; protocol `anthropic` the Messages API,
  <base>/messages.
"""
import json
import os
import shutil
import subprocess
import urllib.request

from . import paths

BACKENDS = ("claude", "open")
CLAUDE_MODELS = ("opus", "sonnet")  # aliases the `claude` CLI accepts; "" is its default model


def backend():
    name = os.environ.get("LLM_BACKEND", "claude").strip().lower() or "claude"
    if name not in BACKENDS:
        raise RuntimeError(f"LLM_BACKEND is {name!r}: use one of {', '.join(BACKENDS)}")
    return name


def settings():
    """(where the model is: the claude CLI or the endpoint URL, the model or "" for Claude Code's default)."""
    if backend() == "open":
        _, base, _, model = open_settings()
        return base, model
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("Claude Code is not on PATH: install it and log in with `claude`, or set LLM_BACKEND=open")
    return exe, os.environ.get("LLM_MODEL", "")


def label():
    """The model as the logs of step 5 name it: `claude-code`, `claude-code:opus`, `open:qwen3.6:35b-a3b-coding`."""
    model = settings()[1]
    if backend() == "open":
        return f"open:{model}"
    return f"claude-code:{model}" if model else "claude-code"


def complete(prompt, system=""):
    """The model's text answer to one prompt."""
    return open_complete(prompt, system) if backend() == "open" else claude_complete(prompt, system)


def claude_complete(prompt, system=""):
    """Claude Code's text answer to one prompt (the prompt goes on stdin: it holds the whole report)."""
    exe, model = settings()
    command = [exe, "-p", "--output-format", "json", "--tools", "", "--disable-slash-commands",
               "--strict-mcp-config", "--no-session-persistence", "--system-prompt", system]
    if model:
        command += ["--model", model]
    done = subprocess.run(command, input=prompt, capture_output=True, text=True, timeout=600, cwd=paths.REPO)
    try:
        answer = json.loads(done.stdout)
    except json.JSONDecodeError:
        answer = {"is_error": True, "result": done.stderr.strip() or done.stdout.strip()}
    if done.returncode or answer.get("is_error"):
        raise RuntimeError(f"claude -p failed (exit {done.returncode}): {answer.get('result')}")
    return answer["result"]


def open_settings():
    """(protocol, base URL, key, model) of the open-weights endpoint."""
    protocol = os.environ.get("LLM_PROTOCOL") or os.environ.get("OPEN_PROTOCOL", "openai")
    base = os.environ.get("LLM_BASE_URL") or os.environ.get("OPEN_BASE_URL", "")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPEN_API_KEY", "")
    model = os.environ.get("LLM_MODEL") or os.environ.get("OPEN_MODEL", "")
    if not base or not model or "REPLACE_ME" in f"{base} {key} {model}":
        raise RuntimeError("fill in OPEN_BASE_URL, OPEN_API_KEY and OPEN_MODEL (or LLM_*) in .env.llm")
    return protocol, base.rstrip("/"), key, model


def open_complete(prompt, system="", max_tokens=None):
    """The endpoint's text answer to one prompt, at temperature 0.

    The default budget is OPEN_MAX_OUTPUT (8192): a reasoning model spends part of it thinking before it answers.
    """
    protocol, base, key, model = open_settings()
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


def open_models(timeout=5):
    """Model ids the endpoint serves (<base>/models), the configured one if the list cannot be read; [] unset."""
    try:
        protocol, base, key, model = open_settings()
    except RuntimeError:
        return []
    request = urllib.request.Request(base + "/models", headers={"Authorization": f"Bearer {key}", "x-api-key": key,
                                                                "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            served = [m["id"] for m in json.load(response).get("data", []) if m.get("id")]
    except (OSError, ValueError, KeyError):
        served = []
    return sorted(set(served) | {model}, key=lambda m: (m != model, m))


def models():
    """The models a page can offer: [{"id": "<backend>:<model>", "label", "backend", "model"}], Claude first."""
    found = []
    if shutil.which("claude"):
        found.append({"id": "claude:", "label": "Claude Code default", "backend": "claude", "model": ""})
        found += [{"id": f"claude:{m}", "label": f"Claude Code · {m}", "backend": "claude", "model": m}
                  for m in CLAUDE_MODELS]
    found += [{"id": f"open:{m}", "label": f"{m} (open weights, .env.llm)", "backend": "open", "model": m}
              for m in open_models()]
    return found
