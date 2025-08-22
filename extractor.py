# MangaToolkitV4 (c) 2025 S1riuSS3301
# Licensed under end-user license agreement (EULA). See LICENSE for details.
# Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
from bs4 import BeautifulSoup
from typing import List, Tuple
import re


def extract_image_urls(html: str) -> List[Tuple[int, str]]:
    """
    Возвращает список (page_number, image_url), отсортированный по page_number.
    Ищет теги <img class="page-image ...">. Берёт src, при отсутствии — data-src/srcset.
    """
    soup = BeautifulSoup(html, 'lxml')
    imgs = soup.find_all('img', class_=lambda c: c and 'page-image' in c)
    results: List[Tuple[int, str]] = []
    for img in imgs:
        num = None
        # порядок из data-number или из id="page-<N>"
        if img.has_attr('data-number'):
            try:
                num = int(str(img['data-number']).strip())
            except Exception:
                pass
        if num is None and img.has_attr('id'):
            m = re.search(r'page-(\d+)', str(img['id']))
            if m:
                try:
                    num = int(m.group(1))
                except Exception:
                    pass
        # URL из src / data-src / srcset
        url = None
        if img.has_attr('src'):
            url = img['src']
        elif img.has_attr('data-src'):
            url = img['data-src']
        elif img.has_attr('srcset'):
            # берём первый источник
            url = str(img['srcset']).split()[0]
        if url and num is not None:
            results.append((num, url))
    # сортировка и удаление дублей по номеру (последний выигрывает)
    results.sort(key=lambda x: x[0])
    uniq = {}
    for n, u in results:
        uniq[n] = u
    return sorted(uniq.items(), key=lambda x: x[0])
