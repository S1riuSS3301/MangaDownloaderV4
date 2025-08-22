# MangaToolkitV4 (c) 2025 S1riuSS3301
# Licensed under end-user license agreement (EULA). See LICENSE for details.
# Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
import os
import math
import time
import logging
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


def _pad(num: int, total: int) -> str:
    width = max(3, int(math.log10(total)) + 1 if total > 0 else 3)
    return str(num).zfill(width)


def download_images(session: requests.Session, items: List[Tuple[int, str]], out_dir: str, referer: str, concurrency: int = 6) -> None:
    os.makedirs(out_dir, exist_ok=True)
    log = logging.getLogger('Downloader')

    total = len(items)

    def _fetch(save_num: int, url: str):
        log.info("DOWNLOAD %s -> #%d", url, save_num)
        # локальное имя по расширению
        ext = '.jpg'
        for cand in ['.jpg', '.jpeg', '.png', '.webp']:
            if url.lower().endswith(cand):
                ext = cand
                break
        name = f"{_pad(save_num, total)}{ext}"
        path = os.path.join(out_dir, name)
        # На всякий случай гарантируем каталог (мог быть удалён или не создан при гонке)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception as e:
            log.warning("MKDIR failed for %s: %s", os.path.dirname(path), e)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            log.debug("SKIP exists %s", name)
            return name
        # ретраи
        attempts, delay, max_delay = 4, 1.0, 8.0
        last_exc = None
        for i in range(1, attempts + 1):
            try:
                r = session.get(url, headers={'Referer': referer}, timeout=25, stream=True)
                log.debug("HTTP %s %s (attempt %d)", r.status_code, url, i)
                if r.status_code != 200:
                    last_exc = Exception(f"HTTP {r.status_code}")
                    raise last_exc
                ctype = r.headers.get('Content-Type', '')
                if 'image' not in ctype:
                    last_exc = Exception(f"Bad content-type: {ctype}")
                    raise last_exc
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 14):
                        if chunk:
                            f.write(chunk)
                log.info("SAVED %s", name)
                return name
            except Exception as e:
                last_exc = e
                log.warning("FAIL #%d %s: %s", save_num, url, e)
                if i < attempts:
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)
        if last_exc:
            raise last_exc
        raise RuntimeError('unknown download error')

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(_fetch, n, url) for n, url in items]
        for fut in as_completed(futures):
            fut.result()
