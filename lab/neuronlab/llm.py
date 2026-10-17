"""One request to Claude Code for step 5 (standard library only).

`claude -p` answers one prompt headless: no tools, no skills, no MCP servers, no saved session, and the system
prompt of the caller instead of the one of Claude Code. It uses the login of the `claude` CLI (subscription or
ANTHROPIC_API_KEY). LLM_MODEL (in .env.llm or the environment) picks the model, e.g. `opus` or `claude-opus-5-5`;
without it Claude Code uses its default model.
"""
import json
import os
import shutil
import subprocess

from . import paths


def settings():
    """(path of the claude CLI, LLM_MODEL or "" for the default model of Claude Code)."""
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("Claude Code is not on PATH: install it and log in with `claude`")
    return exe, os.environ.get("LLM_MODEL", "")


def complete(prompt, system=""):
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
