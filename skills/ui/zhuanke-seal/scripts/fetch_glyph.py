#!/usr/bin/env python3
"""Fetch public-domain 说文解字 small-seal (小篆) glyph outlines from
Wikimedia Commons, verifying the license before saving.

Usage:
    python3 fetch_glyph.py --chars 上善若水 [--glyph-dir ./glyphs]

For each character this looks up `File:<char>-seal.svg` on Commons, confirms
the file is Public Domain via the API's license metadata, downloads it, and
appends a provenance line to SOURCES.md in the glyph directory.

Fail-closed: a glyph whose license cannot be confirmed as Public Domain is
NOT saved. A character with no Commons seal outline is reported so the
caller can fall back to a seal-script font the user owns.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "zhuanke-seal-skill/1.0 (agent skill; glyph provenance fetch)"
PACE_SECONDS = 1.5  # be polite to Commons; it 429s rapid-fire requests


def http_get(url: str, tries: int = 4) -> bytes:
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = float(e.headers.get("Retry-After") or 2 ** (attempt + 1))
                print(f"    rate-limited, retrying in {wait:.0f}s…")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def api_query(title: str) -> dict:
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "format": "json",
    })
    return json.loads(http_get(f"{API}?{params}"))


def license_of(imageinfo: dict) -> str:
    meta = imageinfo.get("extmetadata", {})
    short = meta.get("LicenseShortName", {}).get("value", "")
    terms = meta.get("UsageTerms", {}).get("value", "")
    return short or terms or "unknown"


def fetch_one(char: str, glyph_dir: Path) -> bool:
    title = f"File:{char}-seal.svg"
    dest = glyph_dir / f"{char}-seal.svg"
    if dest.exists():
        print(f"  {char}: already present ({dest.name})")
        return True

    data = api_query(title)
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    info = (page.get("imageinfo") or [{}])[0]
    if "missing" in page or not info.get("url"):
        print(f"  {char}: NO Commons seal outline ({title} not found) — "
              f"fall back to a seal-script font for this character")
        return False

    lic = license_of(info)
    if "public domain" not in lic.lower():
        print(f"  {char}: SKIPPED — license is '{lic}', not confirmed Public Domain")
        return False

    dest.write_bytes(http_get(info["url"]))

    sources = glyph_dir / "SOURCES.md"
    if not sources.exists():
        sources.write_text(
            "# 小篆 glyph sources\n\n"
            "Public-domain 说文解字 small-seal outlines from Wikimedia Commons.\n"
            "These are the authority, not a starting point: 小篆 forms diverge\n"
            "sharply from modern glyphs. Compare every glyph against its Commons\n"
            "page before cutting.\n\n"
            "| File | Char | License | Source |\n| --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    with sources.open("a", encoding="utf-8") as f:
        f.write(f"| `{dest.name}` | {char} | {lic} | "
                f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title)} |\n")
    print(f"  {char}: saved ({lic})")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chars", required=True, help="characters to fetch, e.g. 上善若水")
    ap.add_argument("--glyph-dir", default="./glyphs", help="directory for glyph SVGs")
    args = ap.parse_args()

    glyph_dir = Path(args.glyph_dir)
    glyph_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for i, char in enumerate(args.chars):
        if i:
            time.sleep(PACE_SECONDS)
        try:
            ok = fetch_one(char, glyph_dir)
        except Exception as e:  # keep going; report the character as missing
            print(f"  {char}: FAILED ({e})")
            ok = False
        if not ok:
            missing.append(char)
    if missing:
        print(f"\nNot available as PD Commons outlines: {''.join(missing)}")
        return 1
    print("\nAll glyphs fetched with confirmed Public Domain provenance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
