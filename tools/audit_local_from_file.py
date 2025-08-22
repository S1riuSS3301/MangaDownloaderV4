#!/usr/bin/env python3
"""
MangaToolkitV4 (c) 2025 S1riuSS3301
Licensed under end-user license agreement (EULA). See LICENSE for details.
Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
"""
import re
import sys
import pathlib

DEFAULT_FILE = "/home/sirius/Manga/manga_main_page.html"

def parse_ids(html: str):
    # Ищем все /manga/<slug>/chapter/(\d+-[0-9][0-9\.]*)
    ids = set()
    for m in re.finditer(r"/manga/[\w\-]+/chapter/(\d+-[0-9][0-9\.]*)", html):
        ids.add(m.group(1))
    def key_fn(s: str):
        a, b = s.split('-')
        return (int(a), [int(x) for x in b.split('.')])
    return sorted(ids, key=key_fn)

def main():
    # принимем путь к HTML первым аргументом или используем дефолт
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
    p = pathlib.Path(file_path)
    try:
        html = p.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"[ERR] READ: {e}")
        return 2
    ids = parse_ids(html)
    print(f"Файл: {file_path}")
    print(f"Найдено глав: {len(ids)}")
    if ids:
        print(f"Диапазон: [{ids[0]} .. {ids[-1]}]")
    majors = sorted({int(x.split('-')[0]) for x in ids})
    print(f"Томов (major): {len(majors)}")
    for M in majors:
        minors = [x.split('-')[1] for x in ids if int(x.split('-')[0]) == M]
        if minors:
            print(f"Том {M:02d}: глав={len(minors)} диапазон=[{minors[0]} .. {minors[-1]}]")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
