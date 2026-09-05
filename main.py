import os
import asyncio
import logging
from threading import Thread
from flask import Flask

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
import yt_dlp

# 1. Створюємо веб-сервер для "Health Check" на Render
app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is alive!", 200


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# 2. Основна логіка Telegram-бота
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Токен зчитується з налаштувань середовища

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def download_audio(url: str, output_path: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_path}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = f"{output_path}/{info['id']}.mp3"
        return file_path, info.get('title', 'Audio')


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привіт! Надішли мені посилання на YouTube, і я завантажу аудіо в MP3.")


@dp.message(F.text.contains("youtu"))
async def handle_youtube(message: Message):
    status_msg = await message.answer("📥 Завантажую аудіо, зачекайте...")
    download_dir = "temp_downloads"
    os.makedirs(download_dir, exist_ok=True)

    try:
        loop = asyncio.get_running_loop()
        file_path, title = await loop.run_in_executor(
            None, download_audio, message.text.strip(), download_dir
        )

        await status_msg.edit_text("📤 Відправляю аудіофайл...")

        audio_file = FSInputFile(file_path, filename=f"{title}.mp3")
        await message.answer_audio(audio=audio_file, caption=title)

        if os.path.exists(file_path):
            os.remove(file_path)

        await status_msg.delete()

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("❌ Помилка завантаження. Перевірте посилання.")


async def main():
    logging.basicConfig(level=logging.INFO)

    # Запускаємо веб-сервер у фоновому потоці
    Thread(target=run_flask, daemon=True).start()

    # Запускаємо бота
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
