"""Evidence store: content-addressed raw captures plus a hash-chained log.

Every fetched artifact lands as:
  store/<sha256>.bin        raw response bytes
  store/<sha256>.meta.json  retrieval metadata
and one appended entry in chain.jsonl:

  {"seq": n, "ts": ..., "action": "capture", "artifact": "<sha256>",
   "url": ..., "source": ..., "archive_url": ...,
   "prev_hash": "<sha256 of previous entry>", "entry_hash": "<sha256>"}

entry_hash = sha256(prev_hash + canonical_json(entry_without_entry_hash)).
verify() replays the chain and the artifact bytes.
"""

import hashlib
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

UA = "agent-incident-hunt/0.1 (research; +https://github.com/barlowa124/agent-incident-hunt)"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class EvidenceStore:
    def __init__(self, root="evidence"):
        self.root = Path(root)
        self.store = self.root / "store"
        self.store.mkdir(parents=True, exist_ok=True)
        self.chain_path = self.root / "chain.jsonl"
        self._seq, self._prev = self._tail()

    def _tail(self):
        seq, prev = 0, "0" * 64
        if self.chain_path.exists():
            with open(self.chain_path) as f:
                for line in f:
                    if line.strip():
                        e = json.loads(line)
                        seq, prev = e["seq"], e["entry_hash"]
        return seq, prev

    def _append(self, action, **fields):
        # Serialize writers across processes: hold an exclusive lock on a
        # sidecar file, re-read the tail inside the lock, then append.
        # Without this, two EvidenceStore instances each compute seq from
        # their own stale tail and produce a forked chain.
        import fcntl
        lock_path = self.chain_path.with_suffix(".lock")
        with open(lock_path, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self._seq, self._prev = self._tail()
            entry = {
                "seq": self._seq + 1,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "action": action,
                "prev_hash": self._prev,
                **fields,
            }
            entry["entry_hash"] = hashlib.sha256(
                self._prev.encode() + canonical(entry)
            ).hexdigest()
            with open(self.chain_path, "a") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
            self._seq, self._prev = entry["seq"], entry["entry_hash"]
            return entry

    def put_bytes(self, data: bytes, url: str, source: str, archive_url: str = None):
        sha = hashlib.sha256(data).hexdigest()
        (self.store / f"{sha}.bin").write_bytes(data)
        meta = {
            "sha256": sha,
            "bytes": len(data),
            "url": url,
            "source": source,
            "archive_url": archive_url,
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        (self.store / f"{sha}.meta.json").write_text(
            json.dumps(meta, indent=2, sort_keys=True))
        self._append("capture", artifact=sha, url=url, source=source,
                     archive_url=archive_url)
        return meta

    def record(self, action: str, **fields):
        """Log a non-capture event (triage decision, pivot run, case write)."""
        return self._append(action, **fields)

    def fetch(self, url: str, source: str, archive_url: str = None,
              timeout=30, ua=UA):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            self.record("fetch_error", url=url, source=source,
                        status=e.code)
            raise
        return self.put_bytes(data, url, source, archive_url)

    def get(self, sha: str) -> bytes:
        return (self.store / f"{sha}.bin").read_bytes()

    def meta(self, sha: str) -> dict:
        return json.loads((self.store / f"{sha}.meta.json").read_text())

    def verify(self) -> list:
        """Return a list of problems; empty means chain + artifacts check out."""
        problems = []
        prev, seq = "0" * 64, 0
        if not self.chain_path.exists():
            return ["no chain.jsonl"]
        with open(self.chain_path) as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                e = json.loads(line)
                seq += 1
                if e["seq"] != seq:
                    problems.append(f"line {lineno}: seq {e['seq']} != {seq}")
                if e["prev_hash"] != prev:
                    problems.append(f"line {lineno}: prev_hash mismatch")
                recomputed = hashlib.sha256(
                    prev.encode() + canonical(
                        {k: v for k, v in e.items() if k != "entry_hash"})
                ).hexdigest()
                if recomputed != e["entry_hash"]:
                    problems.append(f"line {lineno}: entry_hash mismatch")
                prev = e["entry_hash"]
                art = e.get("artifact")
                if art:
                    p = self.store / f"{art}.bin"
                    if not p.exists():
                        problems.append(f"line {lineno}: artifact {art} missing")
                    elif hashlib.sha256(p.read_bytes()).hexdigest() != art:
                        problems.append(f"line {lineno}: artifact {art} corrupt")
        return problems


def main():
    import sys
    store = EvidenceStore(sys.argv[2] if len(sys.argv) > 2 else "evidence")
    problems = store.verify()
    if problems:
        for p in problems:
            print("FAIL", p)
        sys.exit(1)
    print(f"OK: {store._seq} chained entries, all artifacts verified")


if __name__ == "__main__":
    main()
