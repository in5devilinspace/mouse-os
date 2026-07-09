#!/usr/bin/env python3
"""dev-bridge — Onyx self-fix executor (dev machine or VPS).

Long-polls n8n for approved dev_commands, runs a fix session, posts HMAC results.

Config file (default ~/.dev-bridge/.env on dev PC, /opt/dev-bridge/.env on VPS):
  DEV_BRIDGE_BASE_URL=https://n8n.microtool.dev   # VPS: http://127.0.0.1:5678
  DEV_BRIDGE_BEARER=<HomeBridge bearer>
  DEV_BRIDGE_HMAC_SECRET=<DEVBRIDGE_HMAC_SECRET>
  DEV_BRIDGE_REPO=/path/to/n8n-ultimate-assistant
  DEV_BRIDGE_CLAUDE=claude
  DEV_BRIDGE_MODE=vps          # optional: git pull before each fix
  CLIPROXY_BASE_URL=http://172.19.0.1:8317/v1    # VPS headless Claude Code
  CLIPROXY_API_KEY=sk-...      # cliproxy key
  DEV_BRIDGE_TIMEOUT_SECS=2400
  POLL_INTERVAL=3
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG = pathlib.Path(
    os.environ.get("DEV_BRIDGE_CONFIG", os.environ.get("HOME", "/root") + "/.dev-bridge/.env")
)
if pathlib.Path("/opt/dev-bridge/.env").exists() and "DEV_BRIDGE_CONFIG" not in os.environ:
    DEFAULT_CONFIG = pathlib.Path("/opt/dev-bridge/.env")

PROMPT_TEMPLATE = (SCRIPT_DIR / "fix_prompt.md").read_text(encoding="utf-8")


def load_env() -> dict:
    env: dict[str, str] = {}
    cfg_path = DEFAULT_CONFIG
    if cfg_path.exists():
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for key in (
        "DEV_BRIDGE_BASE_URL",
        "DEV_BRIDGE_BEARER",
        "DEV_BRIDGE_HMAC_SECRET",
        "DEV_BRIDGE_REPO",
        "DEV_BRIDGE_CLAUDE",
        "DEV_BRIDGE_MODE",
        "CLIPROXY_BASE_URL",
        "CLIPROXY_API_KEY",
        "DEV_BRIDGE_TIMEOUT_SECS",
        "POLL_INTERVAL",
        "DEV_BRIDGE_GIT_BRANCH",
    ):
        if os.environ.get(key):
            env[key] = os.environ[key]
    env.setdefault("DEV_BRIDGE_BASE_URL", _default_base_url())
    env.setdefault(
        "DEV_BRIDGE_REPO",
        str(SCRIPT_DIR.parent if SCRIPT_DIR.name == "dev-bridge" else SCRIPT_DIR),
    )
    env.setdefault("DEV_BRIDGE_CLAUDE", "claude")
    env.setdefault("DEV_BRIDGE_TIMEOUT_SECS", "2400")
    env.setdefault("POLL_INTERVAL", "3")
    env.setdefault("DEV_BRIDGE_GIT_BRANCH", "main")
    return env


def _default_base_url() -> str:
    if pathlib.Path("/opt/n8n").exists() or pathlib.Path("/opt/dev-bridge/.env").exists():
        return "http://127.0.0.1:5678"
    return "https://n8n.microtool.dev"


CFG = load_env()
BASE = CFG["DEV_BRIDGE_BASE_URL"].rstrip("/")
BEARER = CFG.get("DEV_BRIDGE_BEARER", "")
SECRET = CFG.get("DEV_BRIDGE_HMAC_SECRET", "").encode()
REPO = pathlib.Path(CFG["DEV_BRIDGE_REPO"]).resolve()
CLAUDE = CFG.get("DEV_BRIDGE_CLAUDE", "claude")
TIMEOUT = int(CFG["DEV_BRIDGE_TIMEOUT_SECS"])
POLL = max(1, int(CFG.get("POLL_INTERVAL", "3")))
MODE = CFG.get("DEV_BRIDGE_MODE", "vps" if BASE.startswith("http://127.0.0.1") else "dev")
GIT_BRANCH = CFG.get("DEV_BRIDGE_GIT_BRANCH", "main")


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


def git_sync() -> None:
    if MODE != "vps" or not (REPO / ".git").is_dir():
        return
    print(f"[dev-bridge] git pull {GIT_BRANCH} in {REPO}", flush=True)
    subprocess.run(
        ["git", "fetch", "origin", GIT_BRANCH],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    subprocess.run(
        ["git", "pull", "--ff-only", "origin", GIT_BRANCH],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )


def claude_env() -> dict[str, str]:
    env = os.environ.copy()
    cliproxy = CFG.get("CLIPROXY_BASE_URL", "").rstrip("/")
    if cliproxy:
        env["ANTHROPIC_BASE_URL"] = cliproxy
        env.setdefault("ANTHROPIC_API_KEY", CFG.get("CLIPROXY_API_KEY", "sk-dev-bridge"))
    return env


def run_claude(prompt: str) -> dict:
    if not REPO.is_dir():
        raise RuntimeError(f"repo not found: {REPO}")
    if not shutil.which(CLAUDE):
        raise RuntimeError(
            f"{CLAUDE} not found on PATH. On VPS: npm i -g @anthropic-ai/claude-code "
            "or set DEV_BRIDGE_CLAUDE to the full path."
        )
    cmd = [CLAUDE, "-p", prompt, "--permission-mode", "acceptEdits"]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        env=claude_env(),
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return {
        "exit_code": proc.returncode,
        "output": out[-50000:],
        "ok": proc.returncode == 0,
    }


def handle(cmd: dict) -> dict:
    git_sync()
    prompt = build_prompt(cmd)
    print(f"[dev-bridge] fix ({MODE}): {cmd.get('title')}", flush=True)
    result = run_claude(prompt)
    return {
        "title": cmd.get("title"),
        "symptom": cmd.get("symptom"),
        "claude_ok": result["ok"],
        "exit_code": result["exit_code"],
        "summary": result["output"][-4000:],
        "mode": MODE,
    }


def post_result(cmd_id: str, status: str, result: dict) -> None:
    ts = str(int(time.time()))
    body = {"id": cmd_id, "status": status, "result": result, "ts": ts}
    if SECRET:
        body["sig"] = sign_result(cmd_id, status, ts)
    api("POST", "/webhook/dev/result", body)


def main() -> int:
    if not BEARER:
        print(f"Set DEV_BRIDGE_BEARER in {DEFAULT_CONFIG}", file=sys.stderr)
        return 1
    print(
        f"[dev-bridge] mode={MODE} polling {BASE}/webhook/dev/poll  repo={REPO}",
        flush=True,
    )
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
