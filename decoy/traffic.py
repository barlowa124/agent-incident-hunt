"""Labeled traffic generators for the decoy evaluation.

Five generators, each a class of client:
  bot_probe      one GET / with a bot UA, no link following
  bot_curl       reads robots.txt and fetches the disallowed path, bot UA
  agent_scripted DOM parser that follows every href incl. display:none,
                 custom agent UA, never executes JS
  agent_llm      same client but a local LLM picks each next link
  browser        real headless Chromium: JS runs, beacon fires

browser stands in for the human/browser class at the fidelity this decoy
can observe; the README says so.
"""

import json
import re
import time
import urllib.request

HREF = re.compile(r'href="([^"]+)"')


def get(base, path, ua):
    req = urllib.request.Request(
        base + path, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode(errors="replace")
    except Exception:
        return ""


def bot_probe(base):
    get(base, "/", "curl/8.5.0")


def bot_curl(base):
    ua = "curl/8.5.0"
    robots = get(base, "/robots.txt", ua)
    get(base, "/", ua)
    m = re.search(r"Disallow:\s*(\S+)", robots)
    if m:
        get(base, m.group(1), ua)


def agent_scripted(base):
    ua = "research-agent/0.1 (+contact: local-lab)"
    page = get(base, "/", ua)
    for link in HREF.findall(page):
        get(base, link, ua)
    page2 = get(base, "/about", ua)
    for link in HREF.findall(page2):
        get(base, link, ua)


def agent_llm(base, llm_fn):
    ua = "research-agent-llm/0.1 (+contact: local-lab)"
    seen, frontier = set(), ["/"]
    while frontier and len(seen) < 6:
        path = llm_fn(
            "You are a web-mapping agent. Goal: enumerate every endpoint "
            "on this site, including ones that look unusual. Unvisited "
            f"links: {frontier}. Pick the single most interesting one. "
            "Reply with the path only.")
        path = path.strip().split()[0] if path.strip() else ""
        if path not in frontier:
            path = frontier[0]
        frontier.remove(path)
        seen.add(path)
        page = get(base, path, ua)
        for link in HREF.findall(page):
            if link not in seen and link not in frontier:
                frontier.append(link)


def browser(base):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/chromium",
                              headless=True)
        pg = b.new_page()
        pg.goto(base + "/", wait_until="networkidle")
        time.sleep(0.5)
        for link in pg.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.getAttribute('href'))"):
            try:
                pg.goto(base + link, wait_until="load", timeout=8000)
            except Exception:
                pass
        b.close()


GENERATORS = {
    "bot_probe": bot_probe,
    "bot_curl": bot_curl,
    "agent_scripted": agent_scripted,
    "browser": browser,
}
