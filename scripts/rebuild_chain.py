"""Rebuild a forked chain.jsonl into a consistent one.

Two EvidenceStore instances once raced and produced interleaved seqs and
broken prev_hash links (repaired 2026-10-30). Because artifacts are
content-addressed, replaying every recorded action in file order into a
fresh chain preserves every artifact binding. A single `repair` entry at
the head records what happened and how many entries were re-chained.

Usage: python3 scripts/rebuild_chain.py [evidence_dir]
Backs up the original chain to chain.forked.jsonl first.
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hunt.evidence import EvidenceStore


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "evidence")
    old = root / "chain.jsonl"
    backup = root / "chain.forked.jsonl"
    shutil.copy(old, backup)
    entries = [json.loads(l) for l in open(old) if l.strip()]

    # fresh chain in place
    old.unlink()
    store = EvidenceStore(root)
    store.record(
        "repair",
        reason="two writers raced and forked seq/prev_hash",
        rechained=len(entries),
        backup=str(backup))
    for e in entries:
        fields = {k: v for k, v in e.items()
                  if k not in ("seq", "ts", "action", "prev_hash", "entry_hash")}
        store.record(e["action"], **fields)
    problems = store.verify()
    print(f"rebuilt {store._seq} entries; verify: {problems or 'OK'}")


if __name__ == "__main__":
    main()
