# MangaToolkitV4 (c) 2025 S1riuSS3301
# Licensed under end-user license agreement (EULA). See LICENSE for details.
# Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
import argparse
import logging
import os
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from logging_setup import setup_logging
from session_manager import SessionManager
from extractor import extract_image_urls
from downloader import download_images


def _pad2(n: int) -> str:
    try:
        return str(int(n)).zfill(2)
    except Exception:
        return str(n)


def extract_meta(html: str, chapter_url: str):
    """Возвращает (manga_slug, tom_label, glava_label, chapter_id).
    tom_label: 'Том NN' если найден, иначе 'Том 01'
    glava_label: 'Глава <id или номер>'
    chapter_id: из URL /chapter/<id>
    """
    # Из URL
    p = urlparse(chapter_url)
    parts = [x for x in p.path.split('/') if x]
    manga_slug = 'manga'
    chapter_id = 'chapter'
    try:
        mi = parts.index('manga')
        manga_slug = parts[mi + 1]
    except Exception:
        pass
    try:
        ci = parts.index('chapter')
        chapter_id = parts[ci + 1]
    except Exception:
        pass

    # Из <title>
    tom_num = None
    glava_num = None
    try:
        soup = BeautifulSoup(html, 'lxml')
        title = soup.title.text if soup.title else ''
        m_t = re.search(r'Том\s*(\d+)', title, re.IGNORECASE)
        if m_t:
            tom_num = m_t.group(1)
        # поддержка десятичных подглав, например 16.5, 72.1, а также возможного дефиса в других форматах
        m_g = re.search(r'Глава\s*([0-9]+(?:\.[0-9]+)*)', title, re.IGNORECASE)
        if m_g:
            glava_num = m_g.group(1)
    except Exception:
        pass

    # Сопоставим с идентификатором из URL, чтобы учесть десятичные подглавы
    url_major = None
    url_minor = None
    m_url = re.match(r'^(\d+)-([0-9][0-9\.]*)$', chapter_id)
    if m_url:
        url_major = int(m_url.group(1))
        url_minor = m_url.group(2)  # строкой, чтобы сохранить десятичные точки

    # Если том не найден в title — возьмём из URL
    if tom_num is None and url_major is not None:
        tom_num = str(url_major)

    # Всегда используем minor из URL для имени главы (сохраняет дробные подглавы)
    if url_minor is not None:
        glava_num = url_minor

    tom_label = f"Том {_pad2(tom_num) if tom_num else '01'}"
    glava_label = f"Глава {glava_num or chapter_id}"
    return manga_slug, tom_label, glava_label, chapter_id


def derive_out_dir(base_downloads: str, chapter_url: str, html: str) -> str:
    """Формирует путь: Downloads/<manga-slug>/Том NN/Глава <id>"""
    manga_slug, tom_label, glava_label, _ = extract_meta(html, chapter_url)
    logging.getLogger('CLI').info('META: slug=%s, tom=%s, glava=%s', manga_slug, tom_label, glava_label)
    return os.path.join(base_downloads, manga_slug, tom_label, glava_label)


def normalize_urls(chapter_url: str, items):
    norm = []
    for n, u in items:
        if u.startswith('http://') or u.startswith('https://'):
            norm.append((n, u))
        else:
            norm.append((n, urljoin(chapter_url, u)))
    return norm


def build_arg_parser():
    p = argparse.ArgumentParser(description='MangaToolkitV4 downloader for mangapoisk.io')
    p.add_argument('--chapter-url', help='Полный URL страницы главы')
    p.add_argument('--slug', help='Слаг манги, например wedding-ring-story-1')
    p.add_argument('--site', default='https://mangapoisk.io', help='Базовый сайт (по умолчанию https://mangapoisk.io)')
    p.add_argument('--out', help='Каталог назначения (по умолчанию формируется автоматически)')
    p.add_argument('--dry-run', action='store_true', help='Только вывести список URL страниц без скачивания')
    p.add_argument('--auto-next', type=int, default=0, help='Скачать также N следующих глав, инкрементируя вторую часть идентификатора A-B')
    p.add_argument('--all', action='store_true', help='Скачать все главы манги, начиная с самой первой до последней')
    p.add_argument('-f', '--force', action='store_true', help='Принудительно перекачивать главы (файлы будут перезаписаны, если это поддерживается)')
    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')

    # Логи
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    setup_logging(log_dir)
    log = logging.getLogger('CLI')

    sm = SessionManager(cfg_path)

    def parse_chapter_id(ch_id: str):
        m = re.match(r'^(\d+)-(\d+)$', ch_id)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def build_url_with_chapter(u: str, new_ch_id: str) -> str:
        up = urlparse(u)
        parts = [x for x in up.path.split('/') if x]
        try:
            ci = parts.index('chapter')
            parts[ci + 1] = new_ch_id
        except Exception:
            pass
        path = '/' + '/'.join(parts)
        return f"{up.scheme}://{up.netloc}{path}"

    def derive_manga_url(u: str) -> str:
        up = urlparse(u)
        parts = [x for x in up.path.split('/') if x]
        try:
            ci = parts.index('chapter')
            parts = parts[:ci]  # обрезаем /chapter/<id>
        except Exception:
            pass
        path = '/' + '/'.join(parts)
        return f"{up.scheme}://{up.netloc}{path}"

    def get_all_chapter_urls(manga_url: str):
        log.info('CLI: GET MANGA: %s', manga_url)
        resp = sm.get(manga_url)
        html_manga = resp.text
        soup = BeautifulSoup(html_manga, 'lxml')
        # Ищем все ссылки на главы в рамках этого же slug
        up = urlparse(manga_url)
        parts = [x for x in up.path.split('/') if x]
        slug = None
        try:
            mi = parts.index('manga')
            slug = parts[mi + 1]
        except Exception:
            pass
        anchors = soup.select('a[href*="/chapter/"]')
        urls = []
        for a in anchors:
            href = a.get('href')
            if not href:
                continue
            full = href if href.startswith('http') else urljoin(manga_url, href)
            if slug and f"/manga/{slug}/chapter/" not in full:
                continue
            urls.append(full)
        # Дополнительно: парсим все вхождения /chapter/A-B(.C...) из HTML (на случай скрытых/ленивых блоков)
        import re as _re
        for m in _re.finditer(r"/manga/([\w\-]+)/chapter/(\d+)-([0-9][0-9\.]*?)\b", html_manga):
            sl2, a, b = m.group(1), m.group(2), m.group(3)
            if slug and sl2 != slug:
                continue
            urls.append(urljoin(manga_url, f"/manga/{sl2}/chapter/{a}-{b}"))
        # нормализуем и уникализируем
        seen = {}
        for u in urls:
            upu = urlparse(u)
            p2 = [x for x in upu.path.split('/') if x]
            cid = None
            try:
                cix = p2.index('chapter')
                cid = p2[cix + 1]
            except Exception:
                pass
            if cid:
                seen[cid] = u
        # сортировка по числам (A, B)
        def sort_key(item):
            cid, urlv = item
            m = re.match(r'^(\d+)-([0-9][0-9\.]*)$', cid)
            if m:
                major = int(m.group(1))
                minor_str = m.group(2)
                parts = [int(x) for x in minor_str.split('.')]
                return (major, parts)
            return (1 << 30, [99999])
        ordered = [u for cid, u in sorted(seen.items(), key=sort_key)]
        log.info('Глав найдено: %d', len(ordered))
        return ordered

    def find_next_chapter_url(html: str, chapter_url: str) -> str | None:
        """Пытается найти URL следующей главы на странице главы.
        Стратегии:
        - link[rel=next]
        - кнопки/ссылки с текстом 'Следующая'/'Вперёд' и т.п.
        - элементы с data-nav="next"
        """
        soup = BeautifulSoup(html, 'lxml')
        # link rel=next
        ln = soup.select_one('link[rel="next"]')
        if ln and ln.get('href'):
            return urljoin(chapter_url, ln['href'])
        # кнопки/якоря по тексту
        for a in soup.find_all('a', href=True):
            txt = (a.get_text() or '').strip().lower()
            if 'следующ' in txt or 'вперёд' in txt or 'next' in txt or 'далее' in txt:
                return urljoin(chapter_url, a['href'])
        # по классам/атрибутам
        cand = soup.select_one('a.next, a.next-chapter, a[rel~="next"], a[aria-label*="След" i], a[title*="След" i]')
        if cand and cand.get('href'):
            return urljoin(chapter_url, cand['href'])
        # data-nav="next"
        a2 = soup.select_one('[data-nav="next"]')
        if a2 and a2.get('href'):
            return urljoin(chapter_url, a2['href'])
        # общий fallback: любой a[href*="/chapter/"] с упоминанием next в классах
        for a in soup.select('a[href*="/chapter/"]'):
            cls = ' '.join(a.get('class') or [])
            if 'next' in cls.lower():
                return urljoin(chapter_url, a.get('href'))
        return None

    def parse_chapter_id_from_url(u: str):
        up = urlparse(u)
        parts = [x for x in up.path.split('/') if x]
        try:
            ci = parts.index('chapter')
            cid = parts[ci + 1]
            m = re.match(r'^(\d+)-([0-9][0-9\.]*)$', cid)
            if m:
                major = int(m.group(1))
                minor_parts = tuple(int(x) for x in m.group(2).split('.'))
                return major, minor_parts
        except Exception:
            pass
        return None

    def chapter_exists(u: str) -> bool:
        try:
            r = sm.get(u)
            if r.status_code != 200:
                return False
            # простая эвристика по наличию картинок
            soup = BeautifulSoup(r.text, 'lxml')
            if soup.find('img') is None:
                return False
            return True
        except Exception:
            return False

    def numeric_next_url(current_url: str, last_id) -> str | None:
        parsed = parse_chapter_id_from_url(current_url)
        if not parsed:
            return None
        a, b_parts = parsed
        # numeric fallback поддерживает только целые главы; для десятичных положимся на список/next
        if len(b_parts) != 1:
            return None
        b = b_parts[0]
        # сначала пробуем увеличить номер главы в томе
        cand = build_url_with_chapter(current_url, f"{a}-{b+1}")
        if chapter_exists(cand):
            return cand
        # если нет — следующий том с главой 1
        cand2 = build_url_with_chapter(current_url, f"{a+1}-1")
        # ограничимся максимумом, если известен
        if last_id and (a+1, (1,)) > last_id:
            return None
        if chapter_exists(cand2):
            return cand2
        return None

    def process_one(chapter_url: str):
        log.info('CLI: GET HTML: %s', chapter_url)
        resp = sm.get(chapter_url)
        try:
            status = resp.status_code
        except Exception:
            status = 'NA'
        html = resp.text
        log.info('CLI: HTTP %s, HTML length=%d', status, len(html) if isinstance(html, str) else -1)

        items = extract_image_urls(html)
        if not items:
            try:
                from bs4 import BeautifulSoup as _BS
                _s = _BS(html, 'lxml')
                _title = _s.title.text.strip() if _s.title else ''
            except Exception:
                _title = ''
            snippet = (html[:200] if isinstance(html, str) else '')
            log.error('Не удалось извлечь изображения из HTML. title="%s" snippet=%r', _title, snippet)
            return 2, html
        items = normalize_urls(chapter_url, items)
        log.info('Найдено страниц: %d', len(items))
        for n, u in items[:5]:
            log.info('PAGE %d: %s', n, u)

        base_downloads = os.path.join(os.path.dirname(__file__), 'Downloads')
        out_dir = args.out or derive_out_dir(base_downloads, chapter_url, html)
        os.makedirs(out_dir, exist_ok=True)

        if args.dry_run:
            for n, u in items:
                print(n, u)
            return 0, html

        try:
            download_images(sm.session, items, out_dir, referer=chapter_url, concurrency=int(sm.config['app']['concurrency']))
            log.info('Готово: %s', out_dir)
            return 0, html
        except Exception as e:
            log.exception('Ошибка при скачивании: %s', e)
            return 2, html

    # Валидация аргументов
    if not args.chapter_url and not args.slug:
        print("[ERR] Укажите либо --chapter-url, либо --slug")
        return 2

    # Режим скачивания по slug без явного chapter-url
    if args.slug and not args.chapter_url:
        base_site = (args.site or 'https://mangapoisk.io').rstrip('/')
        manga_url = f"{base_site}/manga/{args.slug}?tab=chapters"
        all_urls = get_all_chapter_urls(manga_url)
        visited: set[str] = set()
        if all_urls:
            for u in all_urls:
                if u in visited:
                    continue
                visited.add(u)
                st, _ = process_one(u)
                if st != 0:
                    return st
        return 0

    # Основной + авто-продолжение
    # Определим текущий идентификатор главы
    up0 = urlparse(args.chapter_url)
    parts0 = [x for x in up0.path.split('/') if x]
    ch_id = None
    try:
        ci0 = parts0.index('chapter')
        ch_id = parts0[ci0 + 1]
    except Exception:
        pass

    if args.all:
        # 1) Полный список (включает дробные подглавы)
        manga_url = derive_manga_url(args.chapter_url)
        all_urls = get_all_chapter_urls(manga_url)
        visited: set[str] = set()
        last_processed = None
        if all_urls:
            for u in all_urls:
                if u in visited:
                    continue
                visited.add(u)
                st, _ = process_one(u)
                if st != 0:
                    return st
                last_processed = u
        # 2) Дополнительный проход по "следующей" начиная с самой ранней главы
        current_url = all_urls[0] if all_urls else args.chapter_url
        mu_ref = derive_manga_url(args.chapter_url)
        safety = 0
        while current_url and safety < 2000:
            safety += 1
            # Если уже скачивали эту главу — всё равно получим HTML для вычисления next, но не перекачиваем
            if current_url in visited:
                try:
                    resp_nav = sm.get(current_url)
                    html = resp_nav.text
                except Exception:
                    break
            else:
                visited.add(current_url)
                st, html = process_one(current_url)
                if st != 0:
                    return st
            nxt = find_next_chapter_url(html, current_url)
            if not nxt:
                nxt = numeric_next_url(current_url, None)
            if not nxt:
                break
            if "/manga/" in nxt and derive_manga_url(nxt) != mu_ref:
                break
            current_url = nxt
        return 0
    else:
        status, _ = process_one(args.chapter_url)
        if status != 0:
            return status

        # Следующие главы (локальный инкремент)
        if args.auto_next and ch_id:
            parsed = parse_chapter_id(ch_id)
            if parsed:
                major, minor = parsed
                for _ in range(args.auto_next):
                    minor += 1
                    next_id = f"{major}-{minor}"
                    next_url = build_url_with_chapter(args.chapter_url, next_id)
                    log.info('AUTO-NEXT: %s', next_url)
                    st, _ = process_one(next_url)
                    if st != 0:
                        return st

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
