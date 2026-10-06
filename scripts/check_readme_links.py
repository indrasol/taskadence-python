"""Link check of the three READMEs the registries render (S.23b): README.md (PyPI `taskadence`),
packages/taskadence-mcp/README.md (PyPI `taskadence-mcp`) and packages/mcp-node/README.md (npm `@taskadence/mcp`).

PyPI and npm cannot resolve a relative link, and PyPI gives headings no ids, so every link and image must be an
absolute http(s) URL: a relative path or a `#fragment` fails here without a request. Every URL is then fetched (GET,
redirects followed, three tries) and must answer 2xx (429 counts as alive).

    python scripts/check_readme_links.py            # offline part + every URL
    python scripts/check_readme_links.py --offline  # only the "absolute links" rule
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
READMES = ["README.md", "packages/taskadence-mcp/README.md", "packages/mcp-node/README.md"]
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\]\(([^)\s]+)\)")  # [text](target) and ![alt](src)
BARE = re.compile(r"(?<![(<])\bhttps?://[^\s)>\]]+")
# Pages that refuse automated clients whatever the link's health (npmjs.com answers 403 to any non-browser): the
# package behind them is checked through its registry instead.
REGISTRY_FOR = {
    "https://www.npmjs.com/package/@taskadence/mcp": "https://registry.npmjs.org/@taskadence%2fmcp",
}


def links(text: str) -> list[str]:
    prose = INLINE_CODE.sub("", FENCE.sub("", text))
    found = LINK.findall(prose) + BARE.findall(prose)
    return list(dict.fromkeys(u.rstrip(".,;:") for u in found))


def alive(client: httpx.Client, url: str) -> tuple[bool, str]:
    target = REGISTRY_FOR.get(url, url)
    last = ""
    for attempt in range(3):
        try:
            status = client.get(target).status_code
        except httpx.HTTPError as exc:
            last = type(exc).__name__
        else:
            if 200 <= status < 300 or status == 429:
                return True, str(status)
            last = str(status)
            if status < 500:
                break
        time.sleep(2**attempt)
    return False, last


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    failures: list[str] = []
    urls: dict[str, list[str]] = {}
    for rel in READMES:
        for url in links((ROOT / rel).read_text(encoding="utf-8")):
            if not url.startswith(("https://", "http://")):
                failures.append(f"{rel}: {url} is not absolute (PyPI / npm cannot resolve it)")
            else:
                urls.setdefault(url, []).append(rel)
    if not offline:
        headers = {"User-Agent": "taskadence-python readme link check (+https://github.com/indrasol/taskadence-python)"}
        with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
            for url, where in sorted(urls.items()):
                ok, why = alive(client, url)
                if ok:
                    print(f"ok   {why}  {url}")
                else:
                    failures.append(f"{', '.join(where)}: {url} answered {why}")
    print(f"{len(urls)} URLs in {len(READMES)} READMEs; {len(failures)} problem(s)")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
