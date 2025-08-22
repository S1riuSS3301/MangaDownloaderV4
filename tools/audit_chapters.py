#!/usr/bin/env python3
"""
MangaToolkitV4 (c) 2025 S1riuSS3301
Licensed under end-user license agreement (EULA). See LICENSE for details.
Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
"""
import argparse
import re
import sys
import urllib.request
from bs4 import BeautifulSoup  # noqa: F401  # на будущее

DEFAULT_SITE = "https://mangapoisk.io"
DEFAULT_SLUG = "wedding-ring-story-1"

def parse_ids(html: str):
    # Ищем все /manga/<slug>/chapter/A-B(.C...)
    ids = set()
    for m in re.finditer(r"/manga/[\w\-]+/chapter/(\d+-[0-9][0-9\.]*)", html):
        ids.add(m.group(1))
    def key_fn(s: str):
        a, b = s.split('-')
        return (int(a), [int(x) for x in b.split('.')])
    return sorted(ids, key=key_fn)

def main():
    ap = argparse.ArgumentParser(description="Аудит списка глав по slug")
    ap.add_argument("--slug", default=DEFAULT_SLUG, help="Слаг манги, например wedding-ring-story-1")
    ap.add_argument("--site", default=DEFAULT_SITE, help="Базовый сайт, по умолчанию https://mangapoisk.io")
    args = ap.parse_args()

    base = (args.site or DEFAULT_SITE).rstrip('/')
    url = f"{base}/manga/{args.slug}?tab=chapters"

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[ERR] HTTP: {e}")
        return 2
    ids = parse_ids(html)
    print(f"URL: {url}")
    print(f"Всего глав на сайте: {len(ids)}")
    if ids:
        print(f"Диапазон: [{ids[0]} .. {ids[-1]}]")
    # По томам (major=A)
    majors = sorted({int(x.split('-')[0]) for x in ids})
    print(f"Томов (major): {len(majors)}")
    for M in majors:
        minors = [x.split('-')[1] for x in ids if int(x.split('-')[0]) == M]
        if minors:
            print(f"Том {M:02d}: глав={len(minors)} диапазон=[{minors[0]} .. {minors[-1]}]")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
