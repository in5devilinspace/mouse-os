# Research: Default web-agent (browser automation) integration for Mouse OS, a voice-controlled assistive shell for Ubuntu (GNOME Wayland)

> Produced 2026-07-08 by a three-track research workflow (multi-source web research + adversarial fact-check). Refuted claims are flagged below — treat them as corrections.

## Recommendation

Integrate browser-use as the default web agent. It is the only leading web agent that is a native Python library (MIT, ~103k GitHub stars, v0.13.x as of July 2026, ~89% on the WebVoyager benchmark), so Mouse OS can import it directly, launch tasks from voice intents as asyncio coroutines, narrate progress via step callbacks into TTS, and read a structured result when the run finishes — no separate server, no Node.js, no Docker. Installation is fully user-space on Ubuntu (pip wheel plus a Chromium download into the user cache via `uvx browser-use install`), which fits the no-sudo-during-setup constraint; Chromium runs fine headful under GNOME Wayland via XWayland so the user can watch the agent work and say "stop" to cancel. It is LLM-agnostic (Browser Use's own hosted models, OpenAI, Anthropic, Google, or local Ollama), supports persistent logged-in browser profiles, and its `sensitive_data` mechanism keeps passwords out of the LLM — the key requirements for safe "go to my bank and check my balance" style delegation. Note: the "Cursor web agent" the settings text may allude to is real (Cursor 2.0's in-IDE browser tool) but it is locked inside the Cursor IDE with no public API, so it cannot serve as Mouse OS's backend; browser-use is the correct open equivalent.

## Options considered

### browser-use (embedded Python library) — RECOMMENDED

**How:** pip install browser-use into the Mouse OS venv (Python >= 3.11), run `uvx browser-use install` to fetch a user-space Chromium, then from the voice-intent handler create `Agent(task=<spoken request>, llm=..., browser=Browser(headless=False), sensitive_data={...})` and `await agent.run()`; hook per-step callbacks to TTS and speak `history.final_result()` when done.

**Pros:** Native Python, in-process, MIT-licensed and free; top benchmark scores (~89% WebVoyager); model-agnostic including local Ollama; user-space install (no sudo); `sensitive_data` credential masking and persistent Chrome profiles for logged-in sites; step callbacks map cleanly to voice narration; also ships a CLI 3.0 and MCP server if the architecture changes later.

**Cons:** Fast-moving 0.x API with breaking changes between releases (pin the version); LLM API cost and 30-120 s task latency; ~200-300 MB Chromium download on first setup; reliability on complex multi-step sites is good but not perfect, so tasks need timeouts and a needs-human fallback.

### Playwright MCP (microsoft/playwright-mcp) + Mouse OS's own LLM loop

**How:** Run `npx @playwright/mcp@latest` as a local MCP server; Mouse OS acts as an MCP client, feeding accessibility-tree snapshots to its own LLM which chooses tools (browser_navigate, browser_click, browser_type...).

**Pros:** Deterministic, token-efficient accessibility-tree control (good fit for an accessibility product); maintained by Microsoft; works with any MCP-capable client; Linux-first.

**Cons:** No built-in reasoning loop — Mouse OS must implement the full agent loop (planning, retries, stop conditions) itself; requires a Node.js runtime alongside the Python app; more engineering than v1 warrants.

### Skyvern (self-hosted server + REST API)

**How:** `pip install "skyvern[all]"` then `skyvern quickstart` for a local server and UI (full deployment uses Docker Compose + Postgres); Mouse OS POSTs natural-language tasks to http://localhost:8000 via the Python SDK (`Skyvern(base_url="http://localhost:8000").run_task(prompt=...)`) and polls for results.

**Pros:** Best-in-class at form-filling (85.85% WebVoyager for Skyvern 2.0); vision-based so resilient to layout changes; clean task REST API and workflow builder; open source (AGPL core).

**Cons:** Heaviest footprint — background server, database, optionally Docker (Docker install itself needs sudo); overkill for a single-user assistive shell; higher LLM token cost due to vision.

### Nanobrowser (Chrome extension)

**How:** User installs the extension in Chrome, adds their own LLM API keys, and types/speaks tasks into the Chrome side panel where a Planner/Navigator/Validator multi-agent system executes them.

**Pros:** Free, open source, runs in the user's real logged-in browser; zero backend for Mouse OS to maintain.

**Cons:** No programmatic API — it is driven from the Chrome side-panel UI, so Mouse OS cannot submit voice tasks to it or read results back; Chrome-only; unsuitable as an integration backend.

### Cursor browser agent (Anysphere)

**How:** Not integrable: Cursor 2.0's Agent can drive an embedded browser (navigate/click/type/screenshot/console/network) via an internal MCP server, but only inside the Cursor IDE on the local UI host.

**Pros:** Polished, security-audited, has approval modes and origin allowlists; useful mental model for Mouse OS's own confirmation UX.

**Cons:** Requires the Cursor IDE and subscription; designed for web-dev testing, not general errands; no public API for external apps to delegate tasks; explicitly does not work even over Cursor's own SSH remoting — a dead end as a Mouse OS backend.

## Setup steps (recommended method)

- Verify Python: `python3 --version` must be >= 3.11 (current Ubuntu releases ship 3.12+, so no action normally needed).

- Create an isolated venv for the web agent inside Mouse OS's data dir: `python3 -m venv ~/.local/share/mouse-os/webagent-venv && source ~/.local/share/mouse-os/webagent-venv/bin/activate`.

- Install the library (pin the version to survive 0.x API churn): `pip install 'browser-use==0.13.4'` plus `pip install uv python-dotenv`.

- Download a user-space Chromium (no sudo — installs into the user cache): `uvx browser-use install` (or `browser-use install` from the activated venv).

- If Chromium fails to launch with missing-shared-library errors (rare on desktop Ubuntu with GNOME), PRINT this command for the user to run manually rather than attempting sudo: `sudo apt-get install -y libnss3 libatk-bridge2.0-0t64 libgtk-3-0t64 libasound2t64`.

- In the Mouse OS settings screen, collect an LLM provider + API key and write it to `~/.local/share/mouse-os/webagent.env` with mode 600: one of `BROWSER_USE_API_KEY=` (Browser Use hosted models, simplest), `GOOGLE_API_KEY=`, `ANTHROPIC_API_KEY=`, or an Ollama endpoint for fully local operation.

- Wire the voice intent handler: `from browser_use import Agent, Browser, ChatBrowserUse; agent = Agent(task=spoken_request, llm=ChatBrowserUse(), browser=Browser(headless=False), sensitive_data={'https://*.yourbank.com': {'x_password': password}}, max_steps=settings.max_steps)`; register a new-step callback that speaks a one-line summary of each action through TTS, run `history = await agent.run()` inside a timeout, and speak `history.final_result()` (or a needs-human message) when it ends.

- Add the safety layer in settings: a domain allowlist the task prompt is constrained to, a 'confirm before sensitive actions' toggle (a custom browser-use tool that pauses and asks for voice confirmation before submitting payments/transfers/sends), and a global 'stop' voice command that cancels the asyncio task and closes the browser.

- Smoke-test end to end with the canonical task: say a command that maps to `Agent(task='Find the number 1 post on Show HN')` and confirm the Chromium window opens on the GNOME Wayland desktop, steps are narrated, and the result is spoken back.


## Caveats

- The 'Cursor web agent' interpretation is a dead end for integration: Cursor 2.0's browser tool is real and Linux-capable, but it only runs inside the Cursor IDE on the local UI host, needs a Cursor subscription, and has no public API for third-party delegation.
- browser-use is on 0.x versioning and changes fast (0.13.4 released the week of 2026-07-07; imports and Browser/BrowserProfile APIs have changed repeatedly) — pin the exact version and re-test before upgrading.
- Prompt injection is the dominant real-world risk for browser agents (demonstrated against Perplexity Comet by Brave, and formalized in arXiv 2505.13076): a malicious page can instruct the agent to exfiltrate data or act on other tabs. Mitigate with domain allowlists, headful visibility, and mandatory voice confirmation for irreversible actions.
- For banking, v1 should allow read-only tasks (check balance, find a transaction) behind a confirmation gate and explicitly refuse autonomous money movement; keep logins in a persistent browser profile and pass any needed secrets only via browser-use's sensitive_data placeholders so the LLM never sees them.
- First-run download of Chromium is roughly 200-300 MB and needs network; per-task LLM costs and 30-120 s latencies apply (local Ollama removes cost but measurably lowers task success rates).
- Sites with aggressive bot detection or CAPTCHAs will sometimes block the local agent; browser-use's answer is their paid cloud, which a privacy-focused assistive tool may not want as a default.
- `uvx` requires uv; if absent, install it without sudo via `curl -LsSf https://astral.sh/uv/install.sh | sh` (installs to ~/.local/bin) or fall back to `browser-use install` from the venv.


## Fact-check verdicts on this track's load-bearing claims

- **REFUTED** — browser-use is a Python-native library exposing `Agent(task=..., llm=...)` with `await agent.run()`, is MIT-licensed with ~103k GitHub stars, and its latest release (0.13.4) landed the week of 2026-07-07 — checkable at github.com/browser-use/browser-use.
  - Evidence: Checked directly against the GitHub API and PyPI on 2026-07-08. Three of four components are accurate, but the release claim is false, so the compound claim fails as stated. CONFIRMED: (1) Python-native API — the README quickstart at https://github.com/browser-use/browser-use shows `agent = Agent(task="...", llm=ChatBrowserUse(model='openai/gpt-5.5'))` then `history = await agent.run()`; repo language is Python. (2) MIT license — GitHub API reports license spdx_id MIT and the README FAQ states "This open-source library is licensed under the MIT License." (3) Stars — 103,401 stargazers (~103k). REFUTED: (4) The latest release is 0.13.3, not 0.13.4, and it was published 2026-07-01T15:06:07Z — the week BEFORE 2026-07-07 (https://github.com/browser-use/browser-use/releases/tag/0.13.3, confirmed via the GitHub releases/latest API). PyPI (https://pypi.org/pypi/browser-use/json) also reports latest version 0.13.3; no 0.13.4 exists on GitHub releases or PyPI. Practical impact for Mouse OS integration is low: the API, license, and popularity facts hold; only cite 0.13.3 (2026-07-01) as the current release. Also worth noting for integration planning: 0.13.x introduced a Rust-backed beta agent (`from browser_use.beta import Agent`) and CLI 3.0, but the classic Python `Agent` API is explicitly unchanged.
- **CONFIRMED** — browser-use provides a documented `sensitive_data` mechanism that substitutes placeholders so passwords/PII are never sent to the LLM, plus real-browser-profile reuse for logged-in sessions (docs.browser-use.com/open-source/examples/templates/sensitive-data).
  - Evidence: Confirmed against live official docs on 2026-07-07. (1) The exact cited URL exists and is current: https://docs.browser-use.com/open-source/examples/templates/sensitive-data (HTTP 200, meta description "Handle secret information securely and avoid sending PII & passwords to the LLM"). It documents Agent(sensitive_data={...}) with a "How it Works" section: "Text Filtering: The LLM only sees placeholders (x_user, x_pass), we filter your sensitive data from the input text" and "DOM Actions: Real values are injected directly into form fields after the LLM call", plus per-domain credential scoping via URL-pattern keys. (2) Real-browser-profile reuse is documented in the linked Authentication Guide, https://docs.browser-use.com/open-source/customize/browser/authentication — "Real Browser Profiles: Connect to your existing Chrome browser to reuse your authenticated sessions... if you are logged in on Chrome, the agent is, too" (Browser.from_system_chrome()), with details at https://docs.browser-use.com/open-source/customize/browser/real-browser, plus storage_state='auth.json' cookie persistence as a headless alternative. CAVEAT the claim overstates slightly: "never sent to the LLM" holds only for text; the docs' own best practices require use_vision=False because screenshots containing typed secrets are otherwise sent to the LLM ("Set use_vision=False to prevent screenshot leaks"). Note for Mouse OS: the auth guide warns Chrome must be fully closed before profile reuse (debug-mode launch conflicts with a running Chrome), which matters for a desktop assistive shell where the user's browser is typically open. Historical reliability bug reports exist (e.g. github.com/browser-use/browser-use/issues/1062, placeholder typed literally instead of substituted) but concern implementation glitches in old versions, not the existence of the documented mechanism.
- **REFUTED** — browser-use installs entirely in user space on Ubuntu: `pip install browser-use` (Python >= 3.11) followed by `uvx browser-use install` downloads Chromium into the user cache without sudo (per docs.browser-use.com/open-source/quickstart).
  - Evidence: The commands and Python floor are real, but the "entirely user space / no sudo" part is false on Ubuntu. (1) The quickstart (https://docs.browser-use.com/open-source/quickstart, retrieved 2026-07-07) does show `uv pip install browser-use` + `uvx browser-use install`, and pyproject.toml confirms requires-python ">=3.11,<4.0" (https://github.com/browser-use/browser-use/blob/main/pyproject.toml). (2) However, in both the latest PyPI release 0.13.3 (2026-07-01) and current main, `browser_use/cli.py::_run_install_command` appends `--with-deps` whenever platform.system() == 'Linux', executing `uvx playwright install chromium --with-deps --no-shell` (https://github.com/browser-use/browser-use/blob/0.13.3/browser_use/cli.py). Playwright's `--with-deps`/`install-deps` step installs OS packages via apt and requires root/sudo per official Playwright docs (https://playwright.dev/docs/browsers#install-system-dependencies); as non-root it shells out to `sudo apt-get`, which fails in a headless no-sudo session, so `browser-use install` exits non-zero ("Installation failed") on the target machine. Only the Chromium binary download itself is user-space (~/.cache/ms-playwright). Sudo-free alternative for Mouse OS automated setup: run `uvx playwright install chromium --no-shell` directly (no --with-deps) — this is exactly what browser-use's own runtime fallback uses (`uvx playwright install chromium` in browser_use/browser/watchdogs/local_browser_watchdog.py) — and have the user manually run a printed `sudo apt-get install` / `sudo playwright install-deps chromium` line if shared libraries are missing (usually already present on a full GNOME desktop install).
- **CONFIRMED** — Cursor's browser automation exists (GA in Cursor 2.0, cursor.com/docs/agent/tools/browser) but runs only as an in-IDE MCP-driven webview on the local UI host with no external API — confirmed by Cursor's own docs and a Cursor forum staff response about it not working over SSH.
  - Evidence: Every element checks out against primary sources. (1) The docs page exists and confirms the architecture: https://cursor.com/docs/agent/tools/browser — "Browser runs as a secure web view and is controlled using an MCP server running as an extension" and "The browser opens as a pane within Cursor, giving Agent full control through MCP tools." (2) GA in 2.0 confirmed: https://cursor.com/changelog/2-0 — "Browser (GA). Launched in beta in 1.7, browser for Agent is now GA." (3) The forum staff response is real and verbatim: https://forum.cursor.com/t/cursor-browser-works-locally-but-not-over-ssh/158864 — Cursor team member Mohit (Apr 24, 2026): "This is a known limitation – the browser automation MCP currently runs on the local UI host, and its tools don't fully carry over to SSH remote sessions" (partly attributed to a tracked regression in 3.1.17, with a remote.extensionKind workaround that still failed for the reporter). (4) No external API for the in-IDE browser tool: the Cursor CLI capabilities doc (https://cursor.com/docs/cli/using) lists file/search/shell/web tools but no browser tool, and no programmatic endpoint for the IDE browser is documented. CAVEAT on "only": as of Cursor 3.8 (Jun 18, 2026), Cursor CLOUD agents gained a separate "computer use" capability — "Each cloud agent runs in its own isolated VM with a full desktop environment. Agents can use a mouse and keyboard to control the desktop and browser" (https://cursor.com/docs/cloud-agent/capabilities), and cloud agents are triggerable via an external API (https://cursor.com/docs/cloud-agent/api/endpoints). This runs in Cursor-hosted VMs, not on the user's machine, so the claim's practical conclusion for Mouse OS stands: Cursor offers no way to drive browser automation on the local Ubuntu host outside the IDE — but any restatement should say the in-IDE tool is local-only while noting cloud agents now do browser/computer use in Cursor's own VMs.


## Sources

- [Browser Use — GitHub repository (browser-use/browser-use)](https://github.com/browser-use/browser-use)
- [Browser Use — Human Quickstart (official docs)](https://docs.browser-use.com/open-source/quickstart)
- [Browser Use — Sensitive Data handling (official docs)](https://docs.browser-use.com/open-source/examples/templates/sensitive-data)
- [Cursor Docs — Browser (Agent tool)](https://cursor.com/docs/agent/tools/browser)
- [Cursor Blog — Introducing Cursor 2.0 and Composer](https://cursor.com/blog/2-0)
- [Cursor Forum — Cursor browser works locally but not over SSH](https://forum.cursor.com/t/cursor-browser-works-locally-but-not-over-ssh/158864)
- [Playwright MCP — GitHub (microsoft/playwright-mcp)](https://github.com/microsoft/playwright-mcp)
- [Playwright MCP — official Playwright docs](https://playwright.dev/docs/getting-started-mcp)
- [Skyvern — GitHub (Skyvern-AI/skyvern)](https://github.com/skyvern-ai/skyvern)
- [Skyvern Docs — Self-Hosted Overview](https://www.skyvern.com/docs/developers/self-hosted/overview)
- [Nanobrowser — GitHub (nanobrowser/nanobrowser)](https://github.com/nanobrowser/nanobrowser)
- [Firecrawl Blog — 11 Best AI Browser Agents in 2026 (updated Jun 2026)](https://www.firecrawl.dev/blog/best-browser-agents)
- [AIMultiple — Best 30+ Open Source Web Agents in 2026](https://aimultiple.com/open-source-web-agents)
- [Brave — Indirect Prompt Injection in Perplexity Comet](https://brave.com/blog/comet-prompt-injection/)
- [arXiv — The Hidden Dangers of Browsing AI Agents (2505.13076)](https://arxiv.org/html/2505.13076v1)
- [1Password — Closing the credential risk gap for AI agents using a browser](https://1password.com/blog/closing-the-credential-risk-gap-for-browser-use-ai-agents)
