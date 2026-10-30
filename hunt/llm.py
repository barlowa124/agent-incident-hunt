"""Local LLM client for the triage rationale step. Talks to the ollama
daemon on localhost:11434; model name is configurable. Every call is
recorded in the evidence chain with prompt and response text."""

import json
import urllib.request

from .evidence import EvidenceStore

API = "http://localhost:11434/api/generate"
MODEL = "qwen3-vl:4b"


def generate(prompt, model=MODEL, timeout=300, store=None, purpose=None):
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1},
    }).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    text = resp.get("response", "")
    if store:
        store.record("llm_call", model=model, purpose=purpose,
                     prompt_sha256=_sha(prompt),
                     response_sha256=_sha(text),
                     prompt=prompt[:4000], response=text[:4000])
    return text


def _sha(s):
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()
