# MangaToolkitV4 (c) 2025 S1riuSS3301
# Licensed under end-user license agreement (EULA). See LICENSE for details.
# Use permitted only in original, unmodified form for personal/internal, non-commercial purposes.
import logging
import os
from datetime import datetime


def setup_logging(log_dir: str, level: str = "INFO") -> str:
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("run-%Y%m%d-%H%M%S.log")
    log_path = os.path.join(log_dir, ts)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.getLogger("logging_setup").info("Логирование инициализировано: %s", log_path)
    return log_path
