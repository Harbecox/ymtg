import os
import re
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv; load_dotenv()
from aiogram.client.default import DefaultBotProperties

from downloader import YandexMusicDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
YM_TOKEN  = os.environ.get("YM_TOKEN", "")

bot        = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp         = Dispatcher()
downloader = YandexMusicDownloader(ym_token=YM_TOKEN)

YANDEX_MUSIC_RE = re.compile(
    r"https?://music\.yandex\.(ru|com|by|kz|uz)/album/(\d+)/track/(\d+)"
)


def extract_track_id(url: str) -> tuple[str, str] | None:
    m = YANDEX_MUSIC_RE.search(url)
    if m:
        return m.group(2), m.group(3)
    return None


def single_track_keyboard(track_id, album_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬇️ Скачать",  callback_data=f"dl:{track_id}:{album_id or 0}"),
        InlineKeyboardButton(text="🔁 Похожие", callback_data=f"sim:{track_id}:{album_id or 0}"),
    ]])


def tracks_list_keyboard(tracks) -> InlineKeyboardMarkup:
    buttons = []
    for t in tracks:
        artist   = t.artists[0].name if t.artists else "Unknown"
        album_id = t.albums[0].id    if t.albums  else 0
        label    = f"{artist} — {t.title}"
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"dl:{t.id}:{album_id}"),
            InlineKeyboardButton(text="🔁",  callback_data=f"sim:{t.id}:{album_id}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def similar_keyboard(track_id, album_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔁 Похожие", callback_data=f"sim:{track_id}:{album_id or 0}"),
    ]])


async def send_audio_file(chat_id: int, file_path: str, track_info: dict, status_msg=None, track_id=None, album_id=None):
    artist   = track_info.get("artist",      "Unknown Artist")
    title    = track_info.get("title",       "Unknown Title")
    duration = track_info.get("duration_ms", 0) // 1000

    markup = similar_keyboard(track_id, album_id) if track_id else None
    audio = FSInputFile(file_path, filename=f"{artist} - {title}.mp3")
    await bot.send_audio(chat_id=chat_id, audio=audio, title=title, performer=artist, duration=duration, reply_markup=markup)
    if status_msg:
        await status_msg.delete()


# ─── Handlers ────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎵 <b>Яндекс Музыка — загрузчик</b>\n\n"
        "Отправь ссылку на трек:\n"
        "<code>https://music.yandex.ru/album/123/track/456</code>\n\n"
        "или просто название трека / исполнителя — найду и покажу список.\n\n"
        "⚙️ Команды:\n"
        "/start — это сообщение\n"
        "/help  — справка"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться</b>\n\n"
        "<b>По ссылке:</b>\n"
        "Вставь URL трека из Яндекс Музыки:\n"
        "<code>https://music.yandex.ru/album/3192570/track/354095</code>\n\n"
        "<b>По названию:</b>\n"
        "Напиши название трека или исполнителя, например:\n"
        "<code>Dua Lipa Levitating</code>\n"
        "Бот покажет 10 результатов — нажми на трек чтобы скачать или 🔁 для похожих.\n\n"
        "⚠️ Высокое качество (320 kbps) доступно только с токеном подписки."
    )


@dp.message(F.text)
async def handle_message(message: Message):
    text = message.text.strip()

    ids = extract_track_id(text)
    if ids:
        album_id, track_id = ids
        status = await message.answer("🔍 Получаю информацию о треке...")
        try:
            track = await asyncio.to_thread(
                lambda: downloader._client.tracks([track_id])[0]
            )
            artist       = ", ".join(a.name for a in (track.artists or [])) or "Unknown"
            real_album   = track.albums[0].id if track.albums else album_id
            caption      = f"🎵 <b>{artist} — {track.title}</b>"
            await status.edit_text(caption, reply_markup=single_track_keyboard(track_id, real_album))
        except Exception as exc:
            logger.exception("Track info failed for %s", track_id)
            await status.edit_text(f"❌ Ошибка:\n<code>{exc}</code>")
        return

    status = await message.answer("🔍 Ищу треки...")
    try:
        results = await asyncio.to_thread(
            lambda: downloader._client.search(text, type_="track")
        )
        tracks = (results.tracks.results if results.tracks else [])[:10]

        if not tracks:
            await status.edit_text("❌ Ничего не найдено по запросу: " + text)
            return

        await status.edit_text(
            f"🎵 Результаты по запросу <b>{text}</b>:\n<i>нажми на трек ⬇️ или 🔁 для похожих</i>",
            reply_markup=tracks_list_keyboard(tracks),
        )
    except Exception as exc:
        logger.exception("Search failed: %s", text)
        await status.edit_text(f"❌ Ошибка поиска:\n<code>{exc}</code>")


@dp.callback_query(F.data.startswith("dl:"))
async def handle_download(callback: CallbackQuery):
    _, track_id, album_id = callback.data.split(":")
    album_id = album_id if album_id != "0" else None

    await callback.answer()
    status = await callback.message.answer("⏳ Загружаю трек, подожди...")

    try:
        file_path, track_info = await asyncio.to_thread(
            downloader.download_track, track_id, album_id
        )
        await send_audio_file(callback.message.chat.id, file_path, track_info, status, track_id=track_id, album_id=album_id)
    except Exception as exc:
        logger.exception("Download failed for track %s", track_id)
        await status.edit_text(f"❌ Ошибка:\n<code>{exc}</code>")
    finally:
        try:
            if "file_path" in locals():
                Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass


@dp.callback_query(F.data.startswith("sim:"))
async def handle_similar(callback: CallbackQuery):
    _, track_id, _ = callback.data.split(":")

    await callback.answer()
    status = await callback.message.answer("🔍 Ищу похожие треки...")

    try:
        similar = await asyncio.to_thread(
            lambda: downloader._client.tracks_similar(track_id)
        )
        tracks = (similar.similar_tracks or [])[:10]

        if not tracks:
            await status.edit_text("❌ Похожие треки не найдены.")
            return

        await status.edit_text(
            "🔁 <b>Похожие треки:</b>\n<i>нажми на трек ⬇️ или 🔁 для похожих</i>",
            reply_markup=tracks_list_keyboard(tracks),
        )
    except Exception as exc:
        logger.exception("Similar failed for track %s", track_id)
        await status.edit_text(f"❌ Ошибка:\n<code>{exc}</code>")


# ─── Entry point ─────────────────────────────────────────────────────────────

async def main():
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
