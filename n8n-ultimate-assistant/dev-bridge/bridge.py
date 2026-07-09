#!/usr/bin/env python3
"""dev-bridge — Claude Code executor for Onyx self-fix requests.

Runs on Matt's DEV MACHINE (where Claude Code + this repo live). Long-polls the
n8n VPS for approved dev_commands, launches a Claude Code session with skills,
plugins, and MCP servers, then posts HMAC-signed results back.

Config: ~/.dev-bridge/.env
  DEV_BRIDGE_BASE_URL=https://n8n.microtool.dev
  DEV_BRIDGE_BEARER=<same as n8n HomeBridge/DevBridge credential>
  DEV_BRIDGE_HMAC_SECRET=<same as DEVBRIDGE_HMAC_SECRET on n8n>
  DEV_BRIDGE_REPO=/path/to/n8n-ultimate-assistant
  DEV_BRIDGE_CLAUDE=claude
  DEV_BRIDGE_TIMEOUT_SECS=2400
  POLL_INTERVAL=3
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = pathlib.Path.home() / ".dev-bridge"
PROMPT_TEMPLATE = (pathlib.Path(__file__).parent / "fix_prompt.md").read_text(encoding="utf-8")


def load_env() -> dict:
    env: dict[str, str] = {}
    f = HOME / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.setdefault("DEV_BRIDGE_BASE_URL", "https://n8n.microtool.dev")
    env.setdefault("DEV_BRIDGE_REPO", str(pathlib.Path(__file__).resolve().parents[1]))
    env.setdefault("DEV_BRIDGE_CLAUDE", "claude")
    env.setdefault("DEV_BRIDGE_TIMEOUT_SECS", "2400")
    env.setdefault("POLL_INTERVAL", "3")
    return env


CFG = load_env()
BASE = CFG["DEV_BRIDGE_BASE_URL"].rstrip("/")
BEARER = CFG.get("DEV_BRIDGE_BEARER", "")
SECRET = CFG.get("DEV_BRIDGE_HMAC_SECRET", "").encode()
REPO = pathlib.Path(CFG["DEV_BRIDGE_REPO"]).resolve()
CLAUDE = CFG["DEV_BRIDGE_CLAUDE"]
TIMEOUT = int(CFG["DEV_BRIDGE_TIMEOUT_SECS"])
POLL = max(1, int(CFG.get("POLL_INTERVAL", "3")))


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body or {}).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {BEARER}",
            "Content-Type": "application/json",
            "User-Agent": "dev-bridge/1.0",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode() or "{}")


def sign_result(cmd_id: str, status: str, ts: str) -> str:
    return hmac.new(SECRET, f"{cmd_id}.{status}.{ts}".encode(), hashlib.sha256).hexdigest()


def build_prompt(cmd: dict) -> str:
    skills = ", ".join(cmd.get("skills") or []) or "(use best available skills)"
    mcps = ", ".join(cmd.get("mcp_servers") or []) or "(use enabled MCP servers)"
    files = ", ".join(cmd.get("files_hint") or []) or "(discover from repo)"
    return PROMPT_TEMPLATE.format(
        title=cmd.get("title", "Onyx self-fix"),
        symptom=cmd.get("symptom", ""),
        diagnosis=cmd.get("diagnosis") or "Not yet diagnosed — investigate first.",
        fix_brief=cmd.get("fix_brief", ""),
        files_hint=files,
        skills=skills,
        mcp_servers=mcps,
        repo_path=cmd.get("repo_path") or str(REPO),
    )


def run_claude(prompt: str) -> dict:
    if not REPO.is_dir():
        raise RuntimeError(f"repo not found: {REPO}")
    cmd = [CLAUDE, "-p", prompt, "--permission-mode", "acceptEdits"]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return {
        "exit_code": proc.returncode,
        "output": out[-50000:],
        "ok": proc.returncode == 0,
    }


def handle(cmd: dict) -> dict:
    prompt = build_prompt(cmd)
    print(f"[dev-bridge] Claude Code fix: {cmd.get('title')}", flush=True)
    result = run_claude(prompt)
    return {
        "title": cmd.get("title"),
        "symptom": cmd.get("symptom"),
        "claude_ok": result["ok"],
        "exit_code": result["exit_code"],
        "summary": result["output"][-4000:],
    }


def post_result(cmd_id: str, status: str, result: dict) -> None:
    ts = str(int(time.time()))
    body = {"id": cmd_id, "status": status, "result": result, "ts": ts}
    if SECRET:
        body["sig"] = sign_result(cmd_id, status, ts)
    api("POST", "/webhook/dev/result", body)


def main() -> int:
    if not BEARER:
        print("Set DEV_BRIDGE_BEARER in ~/.dev-bridge/.env", file=sys.stderr)
        return 1
    print(f"[dev-bridge] polling {BASE}/webhook/dev/poll  repo={REPO}", flush=True)
    while True:
        try:
            cmd = api("POST", "/webhook/dev/poll", {})
            if cmd and cmd.get("id"):
                try:
                    result = handle(cmd)
                    post_result(cmd["id"], "done" if result.get("claude_ok") else "error", result)
                    print(f"[dev-bridge] done {cmd['id'][:8]} ok={result.get('claude_ok')}", flush=True)
                except Exception as e:
                    post_result(cmd["id"], "error", {"error": str(e)[:500]})
                    print(f"[dev-bridge] error {e}", flush=True)
        except urllib.error.HTTPError as e:
            if e.code != 204:
                print(f"[dev-bridge] poll http {e.code}", flush=True)
        except Exception as e:
            print(f"[dev-bridge] poll: {e}", flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main())
