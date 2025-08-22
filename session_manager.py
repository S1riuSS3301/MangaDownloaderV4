# MangaToolkitV4 (c) 2025 S1riuSS3301
# Licensed under end-user license agreement (EULA). See LICENSE for details.
# Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
import requests
import yaml
import os
from typing import Dict


class SessionManager:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config: Dict = yaml.safe_load(f)
        self.session = requests.Session()
        headers = self.config.get('network', {}).get('headers', {})
        if headers:
            # Normalize headers keys
            self.session.headers.update({
                k.replace('_', '-').title(): v for k, v in headers.items()
            })
        cookie_file = self.config.get('network', {}).get('cookie_file')
        if cookie_file and os.path.exists(cookie_file):
            try:
                import json
                with open(cookie_file, 'r', encoding='utf-8') as cf:
                    cookies = json.load(cf)
                    for c in cookies:
                        self.session.cookies.set(c.get('name'), c.get('value'), domain=c.get('domain'))
            except Exception:
                pass
        self.timeout = self.config.get('app', {}).get('request_timeout', 25)
        self.retry = self.config.get('app', {}).get('retry', {"attempts": 3, "base_delay": 1.0, "max_delay": 8.0})

    def get(self, url: str, referer: str | None = None) -> requests.Response:
        import time
        attempts = int(self.retry.get('attempts', 3))
        delay = float(self.retry.get('base_delay', 1.0))
        max_delay = float(self.retry.get('max_delay', 8.0))
        last_exc = None
        for i in range(1, attempts + 1):
            try:
                headers = {}
                if referer:
                    headers['Referer'] = referer
                resp = self.session.get(url, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                last_exc = Exception(f"Bad status {resp.status_code}")
            except Exception as e:
                last_exc = e
            if i < attempts:
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
        if last_exc:
            raise last_exc
        raise RuntimeError('Request failed without exception')
