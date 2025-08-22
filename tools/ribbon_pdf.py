#!/usr/bin/env python3
"""
MangaToolkitV4 (c) 2025 S1riuSS3301
Licensed under end-user license agreement (EULA). See LICENSE for details.
Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
"""
import argparse
import os
import re
from typing import List, Tuple

from PIL import Image


def natural_key(s: str):
    # Разбиение строки на числа и текст для естественной сортировки
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def find_volume_dirs(base_slug_dir: str) -> List[str]:
    vols = []
    if not os.path.isdir(base_slug_dir):
        return vols
    for name in os.listdir(base_slug_dir):
        p = os.path.join(base_slug_dir, name)
        if os.path.isdir(p) and name.lower().startswith('том '):
            vols.append(p)
    vols.sort(key=natural_key)
    return vols


def find_chapter_dirs(volume_dir: str) -> List[str]:
    chs = []
    for name in os.listdir(volume_dir):
        p = os.path.join(volume_dir, name)
        if os.path.isdir(p) and name.lower().startswith('глава'):
            chs.append(p)
    chs.sort(key=natural_key)
    return chs


def iter_images_in_chapter(ch_dir: str, exts=(".jpg", ".jpeg", ".png", ".webp")) -> List[str]:
    files = []
    for name in os.listdir(ch_dir):
        if os.path.splitext(name)[1].lower() in exts:
            files.append(os.path.join(ch_dir, name))
    files.sort(key=natural_key)
    return files


def load_image_info(path: str) -> Tuple[int, int]:
    with Image.open(path) as im:
        return im.width, im.height


def open_image_rgb(path: str) -> Image.Image:
    im = Image.open(path)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    elif im.mode == "L":
        im = im.convert("RGB")
    return im


def build_ribbons(image_paths: List[str], max_ribbon_height: int) -> List[Image.Image]:
    ribbons: List[Image.Image] = []
    current_batch: List[str] = []
    cur_h = 0
    max_w = 0

    def flush_batch():
        nonlocal current_batch, cur_h, max_w
        if not current_batch:
            return
        # Подготовим размеры
        sizes = [load_image_info(p) for p in current_batch]
        max_w_local = max(w for w, _ in sizes)
        total_h = sum(h for _, h in sizes)
        canvas = Image.new("RGB", (max_w_local, total_h), (255, 255, 255))
        y = 0
        for p in current_batch:
            with open_image_rgb(p) as im:
                # Паддинг до ширины
                if im.width != max_w_local:
                    # центрируем по горизонтали
                    pad = Image.new("RGB", (max_w_local, im.height), (255, 255, 255))
                    pad.paste(im, ((max_w_local - im.width) // 2, 0))
                    im = pad
                canvas.paste(im, (0, y))
                y += im.height
        ribbons.append(canvas)
        # reset
        current_batch = []
        cur_h = 0
        max_w = 0

    # Набираем картинки в ленту до лимита высоты
    for p in image_paths:
        w, h = load_image_info(p)
        if cur_h > 0 and (cur_h + h) > max_ribbon_height:
            flush_batch()
        current_batch.append(p)
        cur_h += h
        max_w = max(max_w, w)
    flush_batch()
    return ribbons


def save_volume_pdf(volume_dir: str, ribbons: List[Image.Image], quality: int, force: bool) -> str:
    out_path = os.path.join(volume_dir, "volume.pdf")
    if os.path.exists(out_path) and not force:
        print(f"[SKIP] {out_path} уже существует (use --force для перезаписи)")
        # освободим память у уже созданных картинок
        for im in ribbons:
            im.close()
        return out_path
    if not ribbons:
        print(f"[WARN] В томе нет картинок: {volume_dir}")
        return out_path
    first, rest = ribbons[0], ribbons[1:]
    first.save(out_path, "PDF", save_all=True, append_images=rest, quality=quality)
    print(f"[OK] Сохранено: {out_path}")
    # Закрываем
    for im in ribbons:
        im.close()
    return out_path


def process_volume(volume_dir: str, max_height: int, quality: int, force: bool) -> None:
    print(f"== Том: {volume_dir}")
    chapters = find_chapter_dirs(volume_dir)
    all_images: List[str] = []
    for ch in chapters:
        imgs = iter_images_in_chapter(ch)
        if not imgs:
            continue
        all_images.extend(imgs)
    if not all_images:
        print(f"[WARN] Нет картинок в томе: {volume_dir}")
        return
    ribbons = build_ribbons(all_images, max_height)
    save_volume_pdf(volume_dir, ribbons, quality, force)


def main():
    ap = argparse.ArgumentParser(description="Сборка PDF-лент по томам из скачанных изображений")
    ap.add_argument("--slug", required=True, help="Слаг манги, например wedding-ring-story-1")
    ap.add_argument("--base", default=os.path.join(os.path.dirname(__file__), "..", "Downloads"), help="Базовый каталог Downloads")
    ap.add_argument("--max-height", type=int, default=25000, help="Максимальная высота одной ленты (px)")
    ap.add_argument("--quality", type=int, default=90, help="Качество PDF сохранения")
    ap.add_argument("-f", "--force", action="store_true", help="Перезаписывать существующие volume.pdf")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    slug_dir = os.path.join(base, args.slug)
    vols = find_volume_dirs(slug_dir)
    if not vols:
        print(f"[ERR] Не найдены тома в {slug_dir}")
        return 2
    for v in vols:
        process_volume(v, args.max_height, args.quality, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
