import os
import re
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv; load_dotenv()
from aiogram.client.default import DefaultBotProperties

from downloader import YandexMusicDownloader

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Bot & Dispatcher ────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]
YM_TOKEN  = os.environ.get("YM_TOKEN", "")   # Yandex Music OAuth token (optional but recommended)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

dp  = Dispatcher()

downloader = YandexMusicDownloader(ym_token=YM_TOKEN)

# ─── Helpers ─────────────────────────────────────────────────────────────────
YANDEX_MUSIC_RE = re.compile(
    r"https?://music\.yandex\.(ru|com|by|kz|uz)/album/(\d+)/track/(\d+)"
)

def extract_track_id(url: str) -> tuple[str, str] | None:
    """Return (album_id, track_id) or None."""
    m = YANDEX_MUSIC_RE.search(url)
    if m:
        return m.group(2), m.group(3)
    return None

# ─── Handlers ────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎵 <b>Яндекс Музыка — загрузчик</b>\n\n"
        "Отправь мне ссылку на трек вида:\n"
        "<code>https://music.yandex.ru/album/123/track/456</code>\n\n"
        "Я скачаю MP3 и пришлю его сюда.\n\n"
        "⚙️ Команды:\n"
        "/start — это сообщение\n"
        "/help  — справка"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться</b>\n\n"
        "1. Открой Яндекс Музыку в браузере.\n"
        "2. Зайди на страницу нужного трека.\n"
        "3. Скопируй URL из адресной строки, он выглядит так:\n"
        "   <code>https://music.yandex.ru/album/3192570/track/354095</code>\n"
        "4. Вставь ссылку в этот чат и отправь.\n\n"
        "⚠️ Для скачивания в высоком качестве (320 kbps) нужен токен "
        "Яндекс Музыки с подпиской. Без токена доступно только низкое качество."
    )

@dp.message(F.text)
async def handle_link(message: Message):
    url = message.text.strip()

    ids = extract_track_id(url)
    if not ids:
        await message.answer(
            "❌ Не распознал ссылку на трек.\n\n"
            "Пример корректной ссылки:\n"
            "<code>https://music.yandex.ru/album/3192570/track/354095</code>"
        )
        return

    album_id, track_id = ids
    status = await message.answer("⏳ Загружаю трек, подожди...")

    try:
        file_path, track_info = await asyncio.to_thread(
            downloader.download_track, track_id, album_id
        )

        artist = track_info.get("artist", "Unknown Artist")
        title  = track_info.get("title",  "Unknown Title")
        duration = track_info.get("duration_ms", 0) // 1000

        audio = FSInputFile(file_path, filename=f"{artist} - {title}.mp3")
        await bot.send_audio(
            chat_id=message.chat.id,
            audio=audio,
            title=title,
            performer=artist,
            duration=duration,
        )
        await status.delete()

    except Exception as exc:
        logger.exception("Download failed for track %s", track_id)
        await status.edit_text(f"❌ Ошибка при загрузке:\n<code>{exc}</code>")
    finally:
        # Clean up the temp file
        try:
            if "file_path" in locals():
                Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass


# ─── Entry point ─────────────────────────────────────────────────────────────
async def main():
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
