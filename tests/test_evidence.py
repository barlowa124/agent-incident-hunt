import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hunt.evidence import EvidenceStore


def test_chain_roundtrip(tmp_path):
    store = EvidenceStore(tmp_path / "ev")
    m1 = store.put_bytes(b"alpha", "https://a.example/", "test")
    m2 = store.put_bytes(b"beta", "https://b.example/", "test")
    store.record("pivot", indicator="x", observations=2)
    assert store.verify() == []
    assert store._seq == 3
    metas = list((tmp_path / "ev" / "store").glob("*.meta.json"))
    assert len(metas) == 2
    chain = [json.loads(l) for l in
             open(tmp_path / "ev" / "chain.jsonl") if l.strip()]
    assert chain[0]["seq"] == 1 and chain[1]["prev_hash"] == chain[0]["entry_hash"]


def test_chain_detects_tamper(tmp_path):
    store = EvidenceStore(tmp_path / "ev")
    m = store.put_bytes(b"alpha", "https://a.example/", "test")
    # corrupt the artifact
    (tmp_path / "ev" / "store" / f"{m['sha256']}.bin").write_bytes(b"evil")
    assert any("corrupt" in p for p in store.verify())


def test_chain_detects_mid_deletion(tmp_path):
    store = EvidenceStore(tmp_path / "ev")
    store.put_bytes(b"alpha", "https://a.example/", "test")
    store.put_bytes(b"beta", "https://b.example/", "test")
    store.record("pivot", indicator="x", observations=2)
    chain = tmp_path / "ev" / "chain.jsonl"
    lines = chain.read_text().splitlines()
    chain.write_text("\n".join(lines[:1] + lines[2:]) + "\n")
    fresh = EvidenceStore(tmp_path / "ev")
    assert any("mismatch" in p or "seq" in p for p in fresh.verify())


def test_tail_truncation_is_undetectable(tmp_path):
    """Documented limit: a hash chain cannot detect truncation of its own
    tail without an external anchor. Asserted here so the limit is pinned
    by a test, stated in README limits."""
    store = EvidenceStore(tmp_path / "ev")
    store.put_bytes(b"alpha", "https://a.example/", "test")
    store.put_bytes(b"beta", "https://b.example/", "test")
    chain = tmp_path / "ev" / "chain.jsonl"
    lines = chain.read_text().splitlines()
    chain.write_text("\n".join(lines[:-1]) + "\n")
    fresh = EvidenceStore(tmp_path / "ev")
    assert fresh.verify() == []


def test_canonical_determinism():
    from hunt.evidence import canonical
    assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})
