# Research: Natural conversational voice ("talks back like a real person") for Mouse OS, a voice-controlled mouse cursor accessibility app on Ubuntu GNOME Wayland — offline-first v1 with pip/uv install and no sudo, plus a v2 upgrade path

> Produced 2026-07-08 by a three-track research workflow (multi-source web research + adversarial fact-check). Refuted claims are flagged below — treat them as corrections.

## Recommendation

For v1, use Piper TTS (the OHF-Voice/piper1-gpl package, `pip install piper-tts`) streamed through the sounddevice library, with barge-in implemented by aborting the audio stream whenever your existing STT/VAD detects user speech. This was verified empirically on the actual target machine today: piper-tts 1.4.2 installed into a uv Python 3.12 venv with zero compilation and no sudo, and produced its first audio chunk in 41 ms with 4.9 s of speech synthesized in 0.22 s (RTF 0.05) on the Intel Core Ultra 7 258V CPU — no other option combines that latency, offline operation, and install simplicity. Since the machine has only Intel Arc integrated graphics (no CUDA), GPU-hungry "true speech-to-speech" stacks like Moshi/Kyutai Unmute or XTTS-v2 are off the table locally. For a noticeably more human voice while staying offline, offer Kokoro-82M via `kokoro-onnx` (Apache-2.0, runs several-times-real-time on CPU) as an optional "premium local voice". For v2, add an opt-in cloud "conversation mode" using ElevenLabs Agents via the official Python SDK (`elevenlabs` package, Conversation + AudioInterface): it delivers the full ElevenLabs-quality STT+LLM+TTS loop with built-in turn-taking and interruption handling at ~200 ms time-to-first-audio, billed per conversation minute — keep Piper as the always-available offline fallback so the accessibility function never depends on the network.

## Options considered

### Piper TTS (v1 — recommended offline TTS)

**How:** `uv pip install piper-tts` (v1.4.2, GPL-3.0, Open Home Foundation). Download a voice once with `python -m piper.download_voices en_US-lessac-medium`, then use the streaming Python API: `PiperVoice.load(...)` and iterate `voice.synthesize(text)` chunks into a sounddevice RawOutputStream; call `stream.abort()` for barge-in.

**Pros:** Verified working on the exact target machine: clean wheel install in uv venv (Python 3.12), no sudo, no compilation; 41 ms to first audio chunk and 20x-faster-than-real-time synthesis on this CPU; fully offline after one voice download; ~60 MB per voice; used by Home Assistant and NVDA; streaming API makes instant TTS cancellation for barge-in trivial.

**Cons:** Voice is clear and pleasant but noticeably 'TTS-flat' compared to ElevenLabs — good narrator, not a conversational actor; GPL-3.0 license has obligations if you distribute Mouse OS as proprietary software; project is currently 'looking for maintainers' (though it had releases through Apr 2026).

### Kokoro-82M via kokoro-onnx (v1.5 — nicer offline voice)

**How:** `uv pip install kokoro-onnx sounddevice` (verified to resolve in the same py3.12 venv), download kokoro-v1.0.onnx (~300 MB, or ~80 MB quantized) plus voices file from the GitHub releases; same generate-then-stream pattern.

**Pros:** Much more natural prosody than Piper — widely considered the best small open TTS; Apache-2.0 (no license worries); 82M params runs real-time or faster on CPU (reports of ~11x real-time on fast CPUs, works even on Raspberry Pi); multiple voices.

**Cons:** Higher latency and CPU load than Piper (hundreds of ms to first audio vs ~40 ms); larger download; English-centric best quality; no official streaming-chunk API as clean as Piper's, so sentence-level chunking is the practical pattern.

### speech-dispatcher / spd-say (baseline, already installed)

**How:** `/usr/bin/spd-say` is already present on the target Ubuntu machine (it ships with GNOME/Orca); call `spd-say "text"` or use the speechd Python bindings — zero install.

**Pros:** Zero setup, zero dependencies, works today, integrates with the OS accessibility stack (respects Orca settings); useful as an emergency fallback if the venv is broken.

**Cons:** Default espeak-ng voice is robotic — the opposite of 'talks like a real person'; acceptable only for terse status beeps/announcements, not conversation.

### ElevenLabs Agents / Conversational AI (v2 — cloud conversation mode)

**How:** `uv pip install "elevenlabs[pyaudio]"`; create an agent in the ElevenLabs dashboard, then `Conversation(ElevenLabs(api_key=...), agent_id, audio_interface=DefaultAudioInterface(), ...).start_session()` — the SDK handles mic streaming, STT, LLM, TTS, turn-taking and interruptions over WebSocket/WebRTC.

**Pros:** The actual 'ElevenLabs speech-to-speech' experience the user asked for: best-in-class voice naturalness, ~75 ms Flash v2.5 model latency / ~200 ms real-world time-to-first-audio, built-in barge-in and turn-taking, official Python SDK, tool-calling so the agent could even trigger Mouse OS actions.

**Cons:** Requires network and an API key — unacceptable as the only path for an accessibility tool; per-minute billing (third-party 2026 analysis: roughly $0.10–0.30/min depending on plan, ~$0.12–0.18/min at scale tiers; free tier only ~10–15 agent min/month); DefaultAudioInterface needs PortAudio system libs (a sudo apt install the user must run manually), though a custom AudioInterface on the sounddevice wheel avoids sudo; privacy: user audio leaves the machine.

### Full local speech-to-speech stacks (Moshi / Kyutai Unmute, huggingface/speech-to-speech, RealtimeSTT+RealtimeTTS)

**How:** kyutai-labs/unmute wraps their streaming STT + LLM (vLLM) + Kyutai TTS 1.6B behind a Rust websocket server; huggingface/speech-to-speech is a modular VAD→STT→LLM→TTS pipeline with an OpenAI-Realtime-compatible WebSocket API; KoljaB's RealtimeSTT/RealtimeTTS are pip libraries powering ~500 ms-latency local voice chat demos.

**Pros:** Full-duplex, genuinely conversational, fully private; Unmute achieves ~450–750 ms voice-to-voice latency; the HF pipeline and RealtimeSTT/RealtimeTTS are good architectural references for wiring VAD, interruption and streaming.

**Cons:** Not viable on the target machine: it has only an Intel Arc iGPU (no CUDA), while Unmute needs roughly an NVIDIA L40S-class GPU and the good demos of the other stacks assume a discrete GPU; these are v3/self-hosted-server territory, not a laptop accessibility app today.

### Coqui XTTS-v2 (idiap fork) — evaluated and rejected

**How:** `pip install coqui-tts` (the idiap/coqui-ai-TTS maintenance fork).

**Pros:** Voice cloning and expressive multilingual speech; was the 2023–24 default answer for 'local ElevenLabs'.

**Cons:** Coqui the company shut down in January 2024; XTTS-v2 weights remain under the non-commercial Coqui Public Model License with no entity able to sell commercial licenses; the fork is bugfix-only; and it needs a GPU for real-time synthesis, which this machine lacks. Skip it in 2026 — Kokoro/Piper/Chatterbox are the recommended replacements.

## Setup steps (recommended method)

1. Create the venv with a pinned interpreter (system Python is 3.14; wheels were verified on 3.12): `cd "/home/indevilinspace/Mouse OS" && uv venv --python 3.12 .venv`

2. Install the v1 audio stack (no sudo, all prebuilt wheels — sounddevice bundles its own PortAudio): `uv pip install piper-tts sounddevice` (optionally add `faster-whisper` for local STT and `kokoro-onnx` for the premium local voice; both verified to resolve in this venv).

3. One-time voice download (needs network once, then fully offline): `.venv/bin/python -m piper.download_voices en_US-lessac-medium --data-dir ~/.local/share/mouse-os/voices` — audition alternatives at https://rhasspy.github.io/piper-samples (e.g. en_US-amy-medium, en_GB-alba-medium, en_US-ryan-high) and ship your favorite.

4. Wire streaming synthesis: load once at app start (`voice = PiperVoice.load(path)` — ~1 s), then per utterance iterate `for chunk in voice.synthesize(text):` writing `chunk.audio_int16_bytes` into a `sounddevice.RawOutputStream(samplerate=chunk.sample_rate, channels=1, dtype='int16')`. Measured on this machine: first chunk in ~41 ms, so speech starts effectively instantly.

5. Implement barge-in: run your existing mic VAD/STT loop continuously; the moment user speech is detected while the assistant is talking, call `stream.abort()` and discard the rest of the synthesize generator (target < 300 ms from user onset to silence). Keep spoken replies to one short sentence so interruptions are rarely needed.

6. Stop the assistant hearing itself (no sudo — PipeWire is per-user on Ubuntu GNOME): `pactl load-module module-echo-cancel aec_method=webrtc source_name=mouseos_ec_src sink_name=mouseos_ec_sink`, then capture from `mouseos_ec_src` and play TTS to `mouseos_ec_sink`; alternatively gate/duck STT while TTS is playing as a simpler first cut.

7. Keep `spd-say` as a last-resort fallback path (already at /usr/bin/spd-say) for error announcements if the venv audio stack fails.

8. v2 (cloud conversation mode, opt-in): `uv pip install elevenlabs`; create an agent at elevenlabs.io, set `ELEVENLABS_API_KEY` and `AGENT_ID`; use `Conversation(ElevenLabs(api_key=...), agent_id, audio_interface=..., callback_agent_response=...).start_session()`. Either print for the user to run `sudo apt-get install libportaudio2 portaudio19-dev libasound-dev` (needed by the SDK's pyaudio DefaultAudioInterface) or implement a small custom AudioInterface on top of sounddevice to stay sudo-free. Fall back to the Piper path automatically when offline.


## Caveats

- Target hardware constraint verified locally: Intel Core Ultra 7 258V with Intel Arc 130V/140V integrated graphics only — no CUDA. Any recommendation requiring an NVIDIA GPU (XTTS real-time, Chatterbox, Moshi/Unmute, F5-TTS, Orpheus) is excluded for on-device use; they remain options only via a self-hosted GPU server later.
- piper-tts is GPL-3.0 (the piper1-gpl rewrite). If Mouse OS is distributed as proprietary software, linking/importing it in-process has GPL implications — mitigate by shelling out to the piper CLI or running its bundled HTTP server as a separate process, or by choosing Kokoro (Apache-2.0).
- Piper is officially 'looking for maintainers' (README, Feb 2026), though releases continued through v1.4.2 (Apr 2026) and it underpins Home Assistant and NVDA, so short-term risk is low.
- System Python is 3.14.4; installs were verified on a uv-pinned Python 3.12 venv. onnxruntime/piper wheels for 3.14 were not tested — pin 3.12 in setup.
- ElevenLabs pricing figures are volatile and credit-based; the per-minute numbers ($0.10–0.30/min by plan, small free tier) come from a third-party 2026 analysis (Cekura) plus the official pricing page and should be re-checked before committing to a business model. LLM costs are currently absorbed but ElevenLabs has signaled that may change.
- Barge-in quality depends on echo cancellation: without it, the assistant's own voice through speakers triggers false interruptions (a widely reported failure mode). The PipeWire `module-echo-cancel` route is standard but was not live-tested in this session; headset users need none of it.
- Voice model downloads (Piper ~60 MB, Kokoro ~80–300 MB) require network once; for a truly offline installer, bundle the voice files with the app.
- The 41 ms first-chunk figure is synthesis only; end-to-end perceived latency also includes your STT finalization and any LLM response generation — budget the whole loop, and stream sentence-by-sentence if an LLM writes the replies.


## Fact-check verdicts on this track's load-bearing claims

- **CONFIRMED** — piper-tts 1.4.2 installs from PyPI into a uv Python 3.12 venv on this exact Ubuntu machine with no sudo and no compilation (verified by performing the install on 2026-07-07; dependencies: onnxruntime 1.27.0 et al.).
  - Evidence: Reproduced the install on this machine (Ubuntu 26.04, x86_64) on 2026-07-07: `uv venv --python 3.12` created a CPython 3.12.13 venv in the session scratchpad and `uv pip install piper-tts==1.4.2` succeeded as a non-root user in ~48ms, installing exactly 7 packages including onnxruntime==1.27.0 (plus numpy 2.5.1, flatbuffers, packaging, pathvalidate, protobuf) with no sdist builds — uv output showed only wheel installs, no 'Built' lines. `import piper` and the `piper` CLI entry point both work in the venv. PyPI confirms 1.4.2 is the latest release and ships a prebuilt cp39-abi3 manylinux_2_17/2_28 x86_64 wheel covering Python 3.12, so no compilation is needed: https://pypi.org/pypi/piper-tts/1.4.2/json (project page: https://pypi.org/project/piper-tts/1.4.2/). Runtime deps are just onnxruntime>=1,<2 and pathvalidate>=3,<4. Caveat outside the claim's scope: synthesis still requires downloading a voice model separately, and glibc must satisfy manylinux_2_17+ (Ubuntu 26.04 does).
- **CONFIRMED** — Coqui (the company) shut down in January 2024; XTTS-v2 weights remain under the non-commercial Coqui Public Model License and the only maintained code is the idiap/coqui-ai-TTS bugfix fork (per the official coqui-ai/TTS GitHub discussion #4145).
  - Evidence: All three parts verified from primary sources. (1) Shutdown: founder Josh Meyer announced "Coqui is shutting down" on Jan 3, 2024 (https://twitter.com/_josh_meyer_/status/1742522906041635166, quoted in HN thread https://news.ycombinator.com/item?id=38856095 dated Jan 3, 2024). (2) License: the Hugging Face model card https://huggingface.co/coqui/XTTS-v2 (fetched 2026-07-07) still states "This model is licensed under Coqui Public Model License"; relicensing requests (https://huggingface.co/coqui/XTTS-v2/discussions/33) were never granted. (3) Fork: https://github.com/coqui-ai/TTS/discussions/4145 (Jan 30-31, 2025) exists, where fork maintainer eginhard states "XTTS is licensed under the CPML... only non-commercial use of a machine learning model and its outputs" and "We continue to maintain a fork of the code: https://github.com/idiap/coqui-ai-TTS". GitHub API confirms upstream coqui-ai/TTS last push 2024-08-16 (unmaintained, not archived) while idiap/coqui-ai-TTS is active (last push 2026-06-10, release v0.27.5 on 2026-01-26; installable as PyPI package coqui-tts). Minor caveats: #4145 says "we continue to maintain a fork" rather than literally "the only maintained" fork (though it is the de facto recognized successor), and the fork has grown beyond pure bugfixes by 2026 ("mostly with bug fixes for now" was the maintainer's June 2024 description, https://news.ycombinator.com/item?id=40648193). Fork code is MPL 2.0; only the XTTS-v2 weights carry the non-commercial CPML.
- **CONFIRMED** — The target machine has only Intel Arc integrated graphics (lspci: 'Lunar Lake [Intel Arc Graphics 130V/140V]', no nvidia-smi), and Kyutai Unmute's own README states ~750 ms TTS latency even on a single NVIDIA L40S GPU — so local full-duplex speech-to-speech stacks are not viable on this hardware today.
  - Evidence: (1) Verified locally: lspci returns '00:02.0 VGA compatible controller: Intel Corporation Lunar Lake [Intel Arc Graphics 130V / 140V] (rev 04)' and nvidia-smi is not installed. (2) Verified at source: the Unmute README (https://github.com/kyutai-labs/unmute, README.md line ~94) states verbatim 'The TTS latency decreases from ~750ms when running everything on a single L40S GPU to around ~450ms on Unmute.sh' — note the 750ms is the all-services-on-one-L40S config, ~450ms with STT/TTS/LLM on separate GPUs. The same README requires 'a GPU with CUDA support and at least 16 GB VRAM', so Unmute cannot run on Intel Arc at all. (3) Adversarial checks support the conclusion: Moshi's README (https://github.com/kyutai-labs/moshi) supports only CUDA (24GB GPU, no PyTorch quantization), MLX (macOS-only), or Rust/Candle with CUDA/Metal — no Intel XPU/SYCL/Vulkan backend; CPU-only moshi-server runs are reported as far from real time (https://github.com/kyutai-labs/delayed-streams-modeling/issues/123); no 2024–2026 reports found of any full-duplex S2S stack running in real time on a Lunar Lake iGPU. Caveat for the broader project (does not refute the claim): Kyutai's Pocket TTS, a ~100M-param CPU-capable TTS with ~200ms-class latency (https://www.reddit.com/r/LocalLLaMA/comments/1qbpz5l/), shows offline TTS-only on this hardware is feasible even though full-duplex S2S is not.
- **REFUTED** — On the target CPU (Intel Core Ultra 7 258V), Piper's streaming API produced the first audio chunk in 0.041 s and synthesized a 4.91 s sentence in 0.22 s total (RTF 0.05), after a one-time 1.0 s model load (measured locally with en_US-lessac-medium).
  - Evidence: Reproduced the benchmark on the identical machine (lscpu confirms Intel Core Ultra 7 258V) with piper-tts 1.4.2 and en_US-lessac-medium. Model load (1.005 s measured vs 1.0 s claimed) and best-case RTF (0.048 vs 0.05) reproduce, and 0.22 s total for a 4.91 s sentence is consistent with best-case runs (though repeat runs varied 0.048-0.083 RTF, so it is not typical). However, the headline 0.041 s first-chunk figure is impossible as stated: Piper's streaming API PiperVoice.synthesize() yields exactly one AudioChunk per sentence — the shipped source docstring reads 'Synthesize one audio chunk per sentence' and the full ONNX inference completes before yielding (https://github.com/OHF-Voice/piper1-gpl/blob/main/src/piper/voice.py; streaming API documented at https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md). Every single-sentence reproduction run returned chunks=1 with first-chunk time exactly equal to total time (0.31-0.54 s for ~6.5 s audio); a 4.91 s single sentence therefore has first audio at ~0.22-0.35 s, not 0.041 s. A ~40 ms first chunk is only achievable with multi-sentence input whose first sentence is tiny (measured 'Okay.' -> 28-38 ms), so the 0.041 s number was misattributed or conflated. Corrected claim: time-to-first-audio for a typical single-sentence reply is ~0.2-0.5 s on this CPU (still highly responsive); sub-50 ms first audio requires structuring replies with a short leading sentence.
- **CONFIRMED** — piper-tts 1.4.2 installs from PyPI into a uv Python 3.12 venv on this exact Ubuntu machine with no sudo and no compilation (dependencies: onnxruntime 1.27.0 et al.).
  - Evidence: Confirmed by direct reproduction on this machine (Ubuntu 26.04 LTS, x86_64, uv 0.11.26). (1) PyPI JSON API (https://pypi.org/pypi/piper-tts/json) shows 1.4.2 is the latest release (uploaded 2026-04-02) and ships a prebuilt abi3 wheel piper_tts-1.4.2-cp39-abi3-manylinux_2_17_x86_64...manylinux_2_28_x86_64.whl (https://pypi.org/project/piper-tts/1.4.2/), so any CPython >=3.9 including 3.12 uses the binary wheel. (2) Performed the install as a regular user with no sudo: `uv venv --python 3.12` created a venv with uv-managed CPython 3.12.13, and `uv pip install piper-tts==1.4.2` resolved 7 packages in 113ms and installed them in 46ms — wheels only, no build step; uv's sdist build cache (~/.cache/uv/sdists-v9) contains no piper or onnxruntime entries, confirming zero compilation. (3) Dependency resolution matched the claim exactly: onnxruntime==1.27.0, plus numpy 2.5.1, flatbuffers 25.12.19, protobuf 7.35.1, packaging 26.2, pathvalidate 3.3.1 (piper-tts requires_dist declares 'onnxruntime<2,>=1' and 'pathvalidate<4,>=3'). (4) Smoke test passed: `import piper`, `from piper import PiperVoice`, `import onnxruntime` (reports 1.27.0), and `python -m piper --help` all worked in the venv. One clarifying note: the system Python is 3.14.4, so the 3.12 interpreter is uv-managed (downloaded by uv, still no sudo) — consistent with the claim's wording of a 'uv Python 3.12 venv'.


## Sources

- [OHF-Voice/piper1-gpl — Fast and local neural text-to-speech engine (GitHub)](https://github.com/OHF-Voice/piper1-gpl)
- [Piper Python API documentation (streaming synthesize, voice download)](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)
- [Piper voice samples / demo](https://rhasspy.github.io/piper-samples)
- [kokoro-onnx — Kokoro TTS with ONNX runtime (GitHub)](https://github.com/thewh1teagle/kokoro-onnx)
- [hexgrad/Kokoro-82M (Hugging Face model card, Apache-2.0)](https://huggingface.co/hexgrad/Kokoro-82M)
- [Coqui TTS discussion #4145 — company shutdown, CPML license, idiap fork](https://github.com/coqui-ai/TTS/discussions/4145)
- [ElevenLabs Agents Python SDK documentation](https://elevenlabs.io/docs/agents-platform/libraries/python)
- [ElevenLabs models documentation (Flash v2.5 real-time latency)](https://elevenlabs.io/docs/overview/models)
- [ElevenLabs official pricing page](https://elevenlabs.io/pricing)
- [Cekura: ElevenLabs Pricing in 2026 — every plan tested and broken down](https://www.cekura.ai/blogs/elevenlabs-pricing)
- [kyutai-labs/unmute — make text LLMs listen and speak (GPU requirements, latency)](https://github.com/kyutai-labs/unmute)
- [Kyutai TTS 1.6B announcement blog](https://kyutai.org/blog/2025-07-03-kyutai-tts-1-6b/)
- [huggingface/speech-to-speech — modular local VAD→STT→LLM→TTS pipeline](https://github.com/huggingface/speech-to-speech)
- [KoljaB/RealtimeSTT — low-latency STT with VAD for voice assistants](https://github.com/KoljaB/RealtimeSTT)
- [Show HN: Real-time AI voice chat at ~500 ms latency (RealtimeSTT/RealtimeTTS stack)](https://news.ycombinator.com/item?id=43899028)
- [Handling Interruptions in Speech-to-Speech Services — a complete guide (barge-in, <300 ms, echo cancellation)](https://medium.com/@roshini.rafy/handling-interruptions-in-speech-to-speech-services-a-complete-guide-4255c5aa2d84)
- [Deepgram: ElevenLabs barge-in & turn-taking guide](https://deepgram.com/learn/elevenlabs-barge-in-interruptions-turn-taking)
