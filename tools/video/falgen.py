#!/usr/bin/env python3
"""Generate Mouse OS promo clips via the Fal AI queue API (Kling v2 master).

Usage:
  FAL_KEY=... python falgen.py board.json outdir --only 1
  FAL_KEY=... python falgen.py board.json outdir --shots 1,2,4,5
Reads shots[].fal_prompt from the board JSON. Submits, polls, downloads mp4s.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

MODEL = "fal-ai/kling-video/v2/master/text-to-video"
QUEUE = "https://queue.fal.run/" + MODEL
# status/result live under the base app id (first two path segments), NOT the
# full model path — using the full path 405s.
BASE_APP = "https://queue.fal.run/fal-ai/kling-video"
KEY = os.environ["FAL_KEY"]
HDRS = {"Authorization": f"Key {KEY}", "Content-Type": "application/json"}


def _req(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=HDRS, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def submit(prompt, duration="5", aspect="16:9"):
    body = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect,
            "negative_prompt": "text, watermark, logo, blur, distortion, "
            "low quality, deformed hands, extra fingers, cartoon"}
    out = _req(QUEUE, "POST", body)
    return out["request_id"]


def wait(req_id, label=""):
    status_url = f"{BASE_APP}/requests/{req_id}/status"
    result_url = f"{BASE_APP}/requests/{req_id}"
    t0 = time.time()
    while True:
        st = _req(status_url)
        s = st.get("status")
        el = int(time.time() - t0)
        print(f"  [{label}] {s} ({el}s)", flush=True)
        if s == "COMPLETED":
            return _req(result_url)
        if s in ("FAILED", "ERROR"):
            raise RuntimeError(f"{label} failed: {st}")
        time.sleep(8)


def download(url, path):
    r = urllib.request.Request(url, headers={"User-Agent": "mouseos"})
    with urllib.request.urlopen(r, timeout=180) as resp, open(path, "wb") as f:
        f.write(resp.read())
    return os.path.getsize(path)


def main():
    board = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    want = None
    for a in sys.argv[3:]:
        if a.startswith("--only"):
            want = {int(sys.argv[sys.argv.index(a) + 1])}
        if a.startswith("--shots"):
            want = {int(x) for x in sys.argv[sys.argv.index(a) + 1].split(",")}
    shots = [s for s in board["shots"] if want is None or s["n"] in want]

    # submit all, then poll all (queue runs them concurrently)
    jobs = []
    for s in shots:
        rid = submit(s["fal_prompt"])
        print(f"submitted shot {s['n']} -> {rid}", flush=True)
        jobs.append((s["n"], rid))
    results = {}
    for n, rid in jobs:
        res = wait(rid, label=f"shot{n}")
        url = res["video"]["url"]
        path = os.path.join(outdir, f"shot{n}.mp4")
        sz = download(url, path)
        print(f"shot {n} -> {path} ({sz//1024} KB)  src={url}", flush=True)
        results[n] = {"path": path, "url": url}
    json.dump(results, open(os.path.join(outdir, "results.json"), "w"), indent=1)
    print("DONE", list(results))


if __name__ == "__main__":
    main()
