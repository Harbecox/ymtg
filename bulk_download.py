"""
bulk_download.py — читает music.xlsx и скачивает треки через YandexMusicDownloader.

Колонки xlsx:
    B — название папки
    C — исполнитель
    D — трек
"""

import logging
import os
import re
from pathlib import Path

import openpyxl
from dotenv import load_dotenv

from downloader import YandexMusicDownloader

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

XLSX_PATH  = Path(os.environ.get("XLSX_PATH", "music.xlsx"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "music"))
YM_TOKEN   = os.environ.get("YM_TOKEN", "")


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()


def main():
    downloader = YandexMusicDownloader(ym_token=YM_TOKEN)

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb.active

    rows = [
        (row[1], row[2], row[3])
        for row in ws.iter_rows(min_row=3, values_only=True)
        if row[1] or row[3]
    ]
    total = len(rows)
    print(f"Всего треков: {total}\n")

    ok = fail = 0
    for i, (folder, artist, title) in enumerate(rows, 1):
        artist = str(artist or "").strip()
        title  = str(title  or "").strip()
        query  = f"{artist} {title}".strip() if artist else title
        dest   = OUTPUT_DIR / _safe_name(folder or artist or f"track_{i}")
        dest.mkdir(parents=True, exist_ok=True)

        print(f"[{i}/{total}] {query} ...", end=" ", flush=True)
        try:
            tmp_path, info = downloader.search_and_download(query)
            filename = _safe_name(f"{info['artist']} - {info['title']}") + ".mp3"
            final = dest / filename
            Path(tmp_path).rename(final)
            print(f"OK → {final}")
            ok += 1
        except Exception as e:
            print(f"ОШИБКА: {e}")
            fail += 1

    print(f"\nГотово. Успешно: {ok}, Ошибок: {fail}")


if __name__ == "__main__":
    main()
