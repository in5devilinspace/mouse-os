"""mouseos — your voice is the pointer.

Subcommands: run (default) · doctor · setup · setup-model · say · grammar
"""
import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

from . import config as config_mod
from . import doctor as doctor_mod
from . import grammar, parser
from .engine import Engine
from .feedback import ConsoleSink, SpeechSink
from .inputs.repl import ReplSource
from .inputs.voice import MuteGate, VoskSource
from .pointer.detect import pick_backend
from .resolve.screen import Screen
from .resolve.windows import detect_screen_size, try_windows_resolver

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_DIR = Path("~/.cache/mouseos").expanduser()
MODEL_NAME = "vosk-model-small-en-us-0.15"


def run_pipeline(source, engine, apps):
    """The whole product: utterances in, actions out."""
    repl = getattr(source, "repl", False)
    for utterance in source:
        intent = parser.parse(utterance, apps=apps, repl=repl)
        engine.handle(intent)
        if engine.done:
            break


def _launcher(cmd):
    subprocess.Popen(shlex.split(cmd), start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _resolve_screen(cfg, override=None):
    spec = override or cfg.get("screen", "auto")
    if spec and spec != "auto":
        w, _, h = spec.partition("x")
        return Screen(int(w), int(h))
    size = detect_screen_size()
    if size:
        return Screen(*size)
    print("mouse !! could not detect screen size — assuming 1920x1080 "
          "(pass --screen WxH to fix)", file=sys.stderr)
    return Screen(1920, 1080)


def _cmd_run(args):
    cfg = config_mod.load(args.config)
    screen = _resolve_screen(cfg, args.screen)
    apps = tuple(cfg["apps"].keys())

    backend, availability = pick_backend(
        prefer=args.pointer or cfg.get("pointer", "auto"), screen=screen)

    gate = MuteGate()
    console = ConsoleSink()
    feedback = console if args.quiet else SpeechSink(console=console,
                                                     mute_gate=gate)
    windows = try_windows_resolver()
    engine = Engine(pointer=backend, screen=screen, feedback=feedback,
                    windows=windows, config=cfg, launcher=_launcher)
    if not cfg.get("start_asleep", True):
        from .intents import Wake
        engine.handle(Wake())

    console.event(f"pointer backend: {backend.name}")
    if availability.status != "ok":
        feedback.say("practice")
        console.error("degraded", f"{availability.reason} — {availability.hint}")

    input_mode = args.input
    if input_mode == "auto":
        model_ok = (MODEL_DIR / MODEL_NAME).is_dir()
        input_mode = "voice" if model_ok else "repl"
        console.event(f"input: {input_mode} (auto)")

    if input_mode == "voice":
        model_dir = MODEL_DIR / MODEL_NAME
        if not model_dir.is_dir():
            console.error("voice", "model missing — run: mouseos setup-model")
            return 1
        source = VoskSource(model_dir, grammar.phrases(apps), mute_gate=gate,
                            on_state=lambda s: None)
        console.event("listening (say 'mouse wake' to begin, "
                      "'mouse quit' then 'confirm quit' to exit)")
    else:
        source = ReplSource()
        console.event("text mode — type commands "
                      "('mouse wake' to begin, 'help' for the list)")

    try:
        run_pipeline(source, engine, apps)
    except KeyboardInterrupt:
        console.event("interrupted")
    return 0


def _cmd_doctor(_args):
    checks = doctor_mod.run_checks()
    print(doctor_mod.render(checks))
    return doctor_mod.exit_code(checks)


def _cmd_setup(_args):
    script = Path(__file__).resolve().parent.parent / "scripts" / "setup-uinput.sh"
    print("Mouse OS needs one-time permission to create virtual input devices.")
    print("Run this yourself (it needs sudo), then log out and back in:\n")
    print(f"  sudo bash {script}\n")
    if script.exists():
        print(script.read_text())
    return 0


def _cmd_setup_model(_args):
    import urllib.request
    import zipfile
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    target = MODEL_DIR / MODEL_NAME
    if target.is_dir():
        print(f"model already present: {target}")
        return 0
    zip_path = MODEL_DIR / "model.zip"
    print(f"downloading {MODEL_URL} (~40 MB)…")
    urllib.request.urlretrieve(MODEL_URL, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(MODEL_DIR)
    zip_path.unlink()
    print(f"done: {target}")
    return 0


def _cmd_say(args):
    cfg = config_mod.load(args.config)
    screen = _resolve_screen(cfg, args.screen)
    apps = tuple(cfg["apps"].keys())
    backend, availability = pick_backend(
        prefer=args.pointer or cfg.get("pointer", "auto"), screen=screen)
    engine = Engine(pointer=backend, screen=screen, feedback=ConsoleSink(),
                    windows=try_windows_resolver(), config=cfg,
                    launcher=_launcher)
    from .intents import Wake
    engine.handle(Wake())
    for utterance in args.utterance:
        engine.handle(parser.parse(utterance, apps=apps, repl=True))
    return 0


def _cmd_grammar(_args):
    for phrase in grammar.phrases():
        print(phrase)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mouseos",
                                 description="Your voice is the pointer.")
    sub = ap.add_subparsers(dest="cmd")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=None, help="path to config.toml")
    common.add_argument("--screen", default=None, help="WIDTHxHEIGHT override")
    common.add_argument("--pointer", default=None,
                        choices=["auto", "abs", "rel", "dummy"])

    run_p = sub.add_parser("run", parents=[common], help="start the agent")
    run_p.add_argument("--input", default="auto",
                       choices=["auto", "repl", "voice"])
    run_p.add_argument("--quiet", action="store_true",
                       help="console feedback only, no TTS")

    sub.add_parser("doctor", help="check what works and how to fix the rest")
    sub.add_parser("setup", help="print the one-time uinput permission setup")
    sub.add_parser("setup-model", help="download the offline voice model")
    say_p = sub.add_parser("say", parents=[common],
                           help="inject utterances once (testing)")
    say_p.add_argument("utterance", nargs="+")
    sub.add_parser("grammar", help="print every phrase the agent understands")

    args = ap.parse_args(argv)
    cmd = args.cmd or "run"
    if cmd == "run" and args.cmd is None:
        args = ap.parse_args(["run"] + (argv or sys.argv[1:]))
    handler = {
        "run": _cmd_run, "doctor": _cmd_doctor, "setup": _cmd_setup,
        "setup-model": _cmd_setup_model, "say": _cmd_say,
        "grammar": _cmd_grammar,
    }[cmd]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
