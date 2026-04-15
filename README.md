# 🎵 Яндекс Музыка — Telegram-бот

Бот принимает ссылку на трек Яндекс Музыки, скачивает его и отправляет MP3 прямо в чат.

---

## Структура проекта

```
yandex_music_bot/
├── bot.py            — основной файл бота (aiogram 3)
├── downloader.py     — загрузчик треков (yandex-music-api)
├── requirements.txt  — зависимости Python
└── README.md
```

---

## Быстрый старт

### 1. Установи зависимости

```bash
pip install -r requirements.txt
```

### 2. Получи токен Telegram-бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram.
2. Выполни команду `/newbot` и следуй инструкциям.
3. Скопируй выданный токен вида `123456:ABC-DEF...`

### 3. (Опционально, но рекомендуется) Получи токен Яндекс Музыки

Без токена бот работает в анонимном режиме — только низкое качество аудио и не все треки доступны.

**Способ получить токен:**

```bash
pip install yandex-music
python -c "
from yandex_music import Client
import yandex_music.utils.request as R
# Метод через yandex-music-token (см. ниже)
"
```

Воспользуйся утилитой [`yandex-music-token`](https://github.com/MarshalX/yandex-music-api/discussions/524):

```bash
pip install yandex-music-token
python -m yandex_music_token
```

Следуй инструкциям — тебе нужно войти через браузер один раз, после чего токен сохранится.

### 4. Задай переменные окружения

#### Linux / macOS

```bash
export BOT_TOKEN="123456:ABC-DEF..."
export YM_TOKEN="y0_AAAA..."   # опционально
```

#### Windows (PowerShell)

```powershell
$env:BOT_TOKEN = "123456:ABC-DEF..."
$env:YM_TOKEN  = "y0_AAAA..."
```

#### Файл `.env` (через python-dotenv — опционально)

```dotenv
BOT_TOKEN=123456:ABC-DEF...
YM_TOKEN=y0_AAAA...
```

И добавь в начало `bot.py`:
```python
from dotenv import load_dotenv; load_dotenv()
```

### 5. Запусти бота

```bash
python bot.py
```

---

## Использование

1. Открой трек на [music.yandex.ru](https://music.yandex.ru) в браузере.
2. Скопируй URL из адресной строки:
   ```
   https://music.yandex.ru/album/3192570/track/354095
   ```
3. Отправь ссылку боту — он пришлёт MP3-файл.

---

## Деплой (постоянная работа)

### Systemd (Linux)

Создай файл `/etc/systemd/system/ymbot.service`:

```ini
[Unit]
Description=Yandex Music Telegram Bot
After=network.target

[Service]
WorkingDirectory=/opt/yandex_music_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
Environment=BOT_TOKEN=123456:ABC-DEF...
Environment=YM_TOKEN=y0_AAAA...

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now ymbot
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t ymbot .
docker run -d \
  -e BOT_TOKEN="..." \
  -e YM_TOKEN="..." \
  --name ymbot ymbot
```

---

## Требования

- Python 3.10+
- Аккаунт Яндекс Музыки (для полного доступа — с подпиской)
- Telegram-бот (от @BotFather)

---

## Ограничения

| Без токена | С токеном (подписка) |
|------------|----------------------|
| ~128 kbps  | до 320 kbps          |
| Не все треки доступны | Все доступные треки |
| Анонимный лимит запросов | Личные лимиты |

> ⚠️ Бот предназначен для личного использования. Соблюдай условия использования Яндекс Музыки.
