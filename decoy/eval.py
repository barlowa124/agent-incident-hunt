"""Decoy evaluation: run each labeled generator against the live server
and score the detector on its own log output.

Requires the server running (decoy/server.py) and writes
results/decoy_eval.json plus a readable summary.
"""

import argparse
import json
import time
from pathlib import Path

import detect
import traffic


def run_eval(base, log_path, rounds=3, llm_fn=None):
    generators = dict(traffic.GENERATORS)
    if llm_fn:
        generators["agent_llm"] = lambda b: traffic.agent_llm(b, llm_fn)
    runs = []
    for label, gen in generators.items():
        for i in range(rounds):
            start = _logsize(log_path)
            try:
                gen(base)
            except Exception as e:
                print(f"  ! {label} run {i}: {e}")
            time.sleep(0.2)
            reqs = _newlines(log_path, start)
            runs.append({"label": label, "run": i, "requests": reqs})
    return runs


def _logsize(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            return f.tell()
    except FileNotFoundError:
        return 0


def _newlines(path, start):
    out = []
    with open(path, "rb") as f:
        f.seek(start)
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8787")
    ap.add_argument("--log", default="results/decoy_requests.jsonl")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--with-llm", action="store_true")
    ap.add_argument("--out", default="results/decoy_eval.json")
    a = ap.parse_args()
    llm_fn = None
    if a.with_llm:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from hunt import llm
        llm_fn = lambda p: llm.generate(p, timeout=120)
    runs = run_eval(a.base, a.log, a.rounds, llm_fn)
    result = detect.evaluate(runs)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    for label, row in result["matrix"].items():
        print(f"{label:16s} -> {row}")


if __name__ == "__main__":
    main()
