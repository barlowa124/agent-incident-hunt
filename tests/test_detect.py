import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decoy"))
import detect


def r(method, path, ua="x", extra=None):
    rec = {"method": method, "path": path, "ua": ua}
    if extra:
        rec.update(extra)
    return rec


def test_beacon_means_browser():
    reqs = [r("GET", "/", "Mozilla/5.0"),
            r("GET", "/static/app.js", "Mozilla/5.0"),
            r("POST", "/api/beacon", "Mozilla/5.0")]
    assert detect.classify(reqs)["class"] == "browser"


def test_hidden_canary_without_js_is_agent():
    reqs = [r("GET", "/", "research-agent/0.1"),
            r("GET", "/about", "research-agent/0.1"),
            r("GET", "/c/deadbeef", "research-agent/0.1",
              {"canary": "deadbeef"})]
    assert detect.classify(reqs)["class"] == "agent"


def test_bot_ua_with_robots_is_bot():
    reqs = [r("GET", "/robots.txt", "curl/8.5"),
            r("GET", "/hidden/deadbeef", "curl/8.5",
              {"canary": "deadbeef"})]
    assert detect.classify(reqs)["class"] == "bot"


def test_single_probe_is_bot():
    assert detect.classify([r("GET", "/", "nmap")])["class"] == "bot"


def test_asset_only_no_beacon_is_bot():
    reqs = [r("GET", "/", "x"), r("GET", "/static/app.js", "x"),
            r("GET", "/about", "x")]
    assert detect.classify(reqs)["class"] == "bot"


def test_link_walker_no_signal_is_unknown():
    reqs = [r("GET", "/", "x"), r("GET", "/about", "x"),
            r("GET", "/docs", "x")]
    assert detect.classify(reqs)["class"] == "unknown"


def test_evaluate_matrix():
    runs = [
        {"label": "a", "requests": [r("GET", "/", "x"),
                                    r("GET", "/c/t", "x", {"canary": "t"})]},
        {"label": "b", "requests": [r("GET", "/", "curl"),
                                    r("GET", "/robots.txt", "curl")]},
    ]
    res = detect.evaluate(runs)
    assert res["matrix"]["a"]["agent"] == 1
    assert res["matrix"]["b"]["bot"] == 1
