# Onyx self-fix: {title}

You are fixing Matt's **n8n Ultimate Assistant (Onyx)** repo after Telegram-approved diagnosis.

## Symptom (what Matt experienced)

{symptom}

## Diagnosis

{diagnosis}

## What done looks like

{fix_brief}

## Repo

`{repo_path}`

## Files to inspect first

{files_hint}

## Skills to use

{skills}

## MCP servers

{mcp_servers}

## Rules

1. Fix the root cause in the repo — prefer `agents/*.json`, `scripts/`, `web-agent/`, `build/`.
2. Do **not** commit secrets, passwords, or API keys from the transcript.
3. Do **not** `git push` unless Matt explicitly asked.
4. Run minimal validation if available (e.g. `python3 scripts/gen-*.py`, lint).
5. Summarize what you changed in plain language at the end.
