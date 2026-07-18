import os
import re
import asyncio
import logging

from deep_translator import GoogleTranslator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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


# ------------------ Taş-Kağıt-Makas / Камень-ножницы-бумага ------------------

TKM_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
TKM_BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

# chat_id -> {"choices": {user_id: (isim, secim)}}
active_games: dict[int, dict] = {}


async def tkm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    active_games[chat_id] = {"choices": {}}

    keyboard = [
        [
            InlineKeyboardButton(TKM_EMOJI["rock"], callback_data="tkm_rock"),
            InlineKeyboardButton(TKM_EMOJI["paper"], callback_data="tkm_paper"),
            InlineKeyboardButton(TKM_EMOJI["scissors"], callback_data="tkm_scissors"),
        ]
    ]
    text = (
        "⚔️ Taş-Kağıt-Makas savaşı başladı! 10 saniyeniz var, seçiminizi yapın!\n"
        "⚔️ Началась битва камень-ножницы-бумага! У вас 10 секунд, чтобы выбрать!"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    asyncio.create_task(resolve_tkm_game(context, chat_id))


async def tkm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    game = active_games.get(chat_id)

    if not game:
        await query.answer(
            "Oyun aktif değil, /tkm ile yeni oyun başlat.\n"
            "Игра не активна, начни новую с /tkm.",
            show_alert=True,
        )
        return

    choice = query.data.replace("tkm_", "")
    user = query.from_user
    name = user.first_name or user.username or "Oyuncu"
    game["choices"][user.id] = (name, choice)

    emoji = TKM_EMOJI[choice]
    await query.answer(f"Seçimin kaydedildi: {emoji}\nТвой выбор сохранён: {emoji}")


async def resolve_tkm_game(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    await asyncio.sleep(10)
    game = active_games.pop(chat_id, None)
    if game is None:
        return

    choices = list(game["choices"].values())

    if len(choices) < 2:
        text = (
            "⏱️ Süre doldu, yeterli oyuncu yok. Oyun iptal edildi.\n"
            "⏱️ Время вышло, недостаточно игроков. Игра отменена."
        )
        await context.bot.send_message(chat_id=chat_id, text=text)
        return

    (name1, choice1), (name2, choice2) = choices[0], choices[1]
    emoji1, emoji2 = TKM_EMOJI[choice1], TKM_EMOJI[choice2]

    if choice1 == choice2:
        result_line = "🤝 Dostluk kazandı!\n🤝 Победила дружба!"
    elif TKM_BEATS[choice1] == choice2:
        result_line = f"🏆 Kazanan: {name1}\n🏆 Победитель: {name1}"
    else:
        result_line = f"🏆 Kazanan: {name2}\n🏆 Победитель: {name2}"

    text = (
        f"⏱️ Süre doldu! / Время вышло!\n\n"
        f"{name1}: {emoji1}\n"
        f"{name2}: {emoji2}\n\n"
        f"{result_line}"
    )
    await context.bot.send_message(chat_id=chat_id, text=text)


async def kalems_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if active_games.pop(chat_id, None) is not None:
        text = "🛑 Oyun durduruldu.\n🛑 Игра остановлена."
    else:
        text = "Aktif oyun yok.\nНет активной игры."
    await update.message.reply_text(text)


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("kalem", tkm_command))
    app.add_handler(CommandHandler("kalems", kalems_command))
    app.add_handler(CallbackQueryHandler(tkm_callback, pattern="^tkm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot başlatıldı, mesajlar dinleniyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
