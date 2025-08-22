#!/usr/bin/env python3
"""
MangaToolkitV4 (c) 2025 S1riuSS3301
Licensed under end-user license agreement (EULA). See LICENSE for details.
Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
"""
import re
import sys
import os
import pathlib
from collections import defaultdict

# входные файлы/каталоги
DEFAULT_HTML_FILE = "/home/sirius/Manga/manga_main_page.html"
DOWNLOADS_DIR = "/home/sirius/Manga/MangaToolkitV4/Downloads"

# slug берём из HTML ссылок
SLUG_RE = re.compile(r"/manga/([\w\-]+)/chapter/(\d+-[0-9][0-9\.]*)")
CH_ID_RE = re.compile(r"^(\d+)-([0-9][0-9\.]*)$")
VOL_DIR_RE = re.compile(r"^Том\s+(\d+)$")


def parse_online_ids(html: str):
    ids = set()
    slug_seen = None
    for m in SLUG_RE.finditer(html):
        slug, cid = m.group(1), m.group(2)
        if slug_seen is None:
            slug_seen = slug
        if slug != slug_seen:
            continue
        ids.add(cid)
    def key_fn(s: str):
        a, b = s.split('-')
        return (int(a), [int(x) for x in b.split('.')])
    return slug_seen, sorted(ids, key=key_fn)


def scan_local_ids(base: str, slug: str):
    result = []
    root = pathlib.Path(base) / slug
    if not root.exists():
        return result
    # Рекурсивно ищем директории 'Глава <minor>' и поднимаемся к ближайшему 'Том NN'
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            if d.startswith('Глава '):
                minor = d.split(' ', 1)[1].strip()
                # определить том по родителям
                vol = None
                p = pathlib.Path(dirpath)
                for ancestor in [p] + list(p.parents):
                    name = ancestor.name
                    m = VOL_DIR_RE.match(name)
                    if m:
                        vol = int(m.group(1))
                        break
                if vol is None:
                    continue
                cid = f"{vol}-{minor}"
                # валидируем minor
                try:
                    int(str(minor).split('.')[0])
                except Exception:
                    continue
                result.append(cid)
    # сортировка
    def key_fn(s: str):
        a, b = s.split('-')
        return (int(a), [int(x) for x in b.split('.')])
    return sorted(set(result), key=key_fn)


def main():
    # путь к HTML можно передать аргументом
    html_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HTML_FILE
    # читаем HTML
    try:
        html = pathlib.Path(html_file).read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"[ERR] READ HTML: {e}")
        return 2
    slug, online_ids = parse_online_ids(html)
    if not slug:
        print("[ERR] Не удалось определить slug из HTML")
        return 2
    # локальные главы
    # локальные главы
    root_scan = str(pathlib.Path(DOWNLOADS_DIR) / slug)
    local_ids = scan_local_ids(DOWNLOADS_DIR, slug)

    # индексация по томам
    def group_by_major(ids):
        g = defaultdict(list)
        for cid in ids:
            a, b = cid.split('-')
            g[int(a)].append(b)
        for k in g:
            # сортировка b
            def key_b(x):
                return [int(t) for t in x.split('.')]
            g[k] = sorted(g[k], key=key_b)
        return dict(sorted(g.items()))

    online_g = group_by_major(online_ids)
    local_g = group_by_major(local_ids)

    # сводка
    print(f"Файл HTML: {html_file}")
    print(f"Slug: {slug}")
    print(f"Онлайн глав (по HTML): {len(online_ids)}")
    print(f"Сканирую локально: {root_scan}")
    print(f"Локально глав: {len(local_ids)}")

    majors = sorted(set(online_g.keys()) | set(local_g.keys()))
    for M in majors:
        on = online_g.get(M, [])
        lo = local_g.get(M, [])
        miss = [x for x in on if x not in lo]
        extra = [x for x in lo if x not in on]
        def rng(vals):
            return f"[{vals[0]} .. {vals[-1]}]" if vals else "[]"
        print(f"Том {M:02d}: online={len(on)} {rng(on)} | local={len(lo)} {rng(lo)} | missing={len(miss)} {miss[:10]}{' ...' if len(miss)>10 else ''}")

    # явные пропуски по томам 04 и 10
    for M in (4, 10):
        on = online_g.get(M, [])
        lo = local_g.get(M, [])
        if on:
            miss = [x for x in on if x not in lo]
            if miss:
                print(f"ВНИМАНИЕ: Том {M:02d} пропущено локально {len(miss)} глав: {miss[:20]}{' ...' if len(miss)>20 else ''}")
            else:
                print(f"Том {M:02d}: все онлайн главы присутствуют локально ({len(on)})")
        else:
            print(f"Том {M:02d}: онлайн-данных в HTML не найдено")

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
