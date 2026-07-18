import os
import re
import logging

from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Kiril alfabesi karakterleri -> mesaj Rusça demektir.
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    # Botlardan (kendisi dahil) gelen mesajları yok say -> sonsuz döngü olmasın.
    if message.from_user and message.from_user.is_bot:
        return

    text = message.text.strip()
    if not text:
        return

    is_russian = bool(CYRILLIC_RE.search(text))
    source_lang = "RU" if is_russian else "TR"
    target_lang = "TR" if is_russian else "RU"

    try:
        translated_text = GoogleTranslator(
            source=source_lang.lower(), target=target_lang.lower()
        ).translate(text)
    except Exception:
        logger.exception("Çeviri başarısız oldu")
        return

    if not translated_text:
        return

    # Orijinal mesaja yanıt (reply/alıntı) olarak çeviriyi gönder.
    await message.reply_text(translated_text)


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot başlatıldı, mesajlar dinleniyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
