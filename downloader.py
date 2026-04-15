"""
downloader.py — обёртка над yandex-music-api для скачивания треков.

Документация SDK: https://yandex-music.readthedocs.io/en/main/
"""

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class YandexMusicDownloader:
    """Скачивает треки с Яндекс Музыки через официальный Python-клиент."""

    def __init__(self, ym_token: str = ""):
        """
        Parameters
        ----------
        ym_token : str
            OAuth-токен Яндекс Музыки.
            Без токена — анонимный доступ (только низкое качество, не все треки).
            С токеном подписки — до 320 kbps.
        """
        from yandex_music import Client

        if ym_token:
            self._client = Client(ym_token).init()
            logger.info("Yandex Music client initialised with token (authorised mode).")
        else:
            self._client = Client().init()
            logger.warning(
                "Yandex Music client initialised WITHOUT token (anonymous mode). "
                "Only low-quality downloads are available."
            )

    # ──────────────────────────────────────────────────────────────────────────
    def download_track(self, track_id: str | int, album_id: str | int | None = None) -> tuple[str, dict]:
        """
        Скачивает трек и возвращает (путь_к_файлу, метаданные).

        Parameters
        ----------
        track_id  : ID трека на Яндекс Музыке.
        album_id  : ID альбома (опционально, нужен для корректной загрузки).

        Returns
        -------
        tuple[str, dict]
            Путь к временному MP3-файлу и словарь с метаданными трека.
        """
        # ── Получаем объект трека ─────────────────────────────────────────────
        track = self._client.tracks([str(track_id)])[0]

        # ── Извлекаем читаемые метаданные ─────────────────────────────────────
        artists = ", ".join(a.name for a in (track.artists or []))
        title   = track.title or "Unknown"
        dur_ms  = track.duration_ms or 0

        track_info = {
            "artist":      artists or "Unknown Artist",
            "title":       title,
            "duration_ms": dur_ms,
            "track_id":    track_id,
            "album_id":    album_id,
        }
        logger.info("Track resolved: %s — %s (%d ms)", artists, title, dur_ms)

        # ── Выбираем наилучшее доступное качество ────────────────────────────
        download_info = track.get_download_info()
        if not download_info:
            raise RuntimeError("Нет доступных вариантов загрузки для этого трека.")

        # Сортируем по битрейту (desc), предпочитаем MP3
        best = sorted(
            download_info,
            key=lambda d: (d.codec == "mp3", d.bitrate_in_kbps),
            reverse=True,
        )[0]
        logger.info("Best quality: codec=%s, bitrate=%s kbps", best.codec, best.bitrate_in_kbps)

        # ── Загружаем в temp-файл ──────────────────────────────────────────────
        suffix = ".mp3" if best.codec == "mp3" else ".aac"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()

        best.download(tmp.name)
        logger.info("Downloaded to %s", tmp.name)

        return tmp.name, track_info
