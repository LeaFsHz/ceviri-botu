import os
import re
import random
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


# Google Translate'in bağlamı kaçırıp yanlış çevirdiği argo/ünlem kelimeler.
# Anahtar küçük harfe çevrilmiş haliyle aranır.
MANUAL_OVERRIDES = {
    "ru_to_tr": {
        "блядь": "siktir",
        "бля": "lan",
        "черт": "kahretsin",
        "пиздец": "eyvah",
        "сука": "orospu çocuğu",
    },
    "tr_to_ru": {
        "siktir": "блядь",
        "lan": "бля",
        "kahretsin": "черт",
        "amk": "бля",
    },
}


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

    override_table = MANUAL_OVERRIDES["ru_to_tr" if is_russian else "tr_to_ru"]
    stripped = text.strip(" .,!?").lower()
    if stripped in override_table:
        await message.reply_text(override_table[stripped])
        return

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


# ------------------ Zar Oyunu / Игра в кости ------------------

DICE_BOARD_LEN = 20

# chat_id -> {"players": [(user_id, isim), ...], "positions": {user_id: konum}, "turn": 0/1, "started": bool}
dice_games: dict[int, dict] = {}


async def zar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    name = user.first_name or user.username or "Oyuncu"

    if chat_id in dice_games:
        await update.message.reply_text(
            "Zaten aktif bir zar oyunu var.\nИгра в кости уже идёт."
        )
        return

    dice_games[chat_id] = {
        "players": [(user.id, name)],
        "positions": {user.id: 0},
        "turn": 0,
        "started": False,
        "rolling": False,
    }
    text = (
        f"🎲 {name} zar oyunu başlattı! Katılmak için butona bas.\n"
        f"🎲 {name} начал(а) игру в кости! Нажми, чтобы присоединиться."
    )
    keyboard = [[InlineKeyboardButton("🙋 Katıl / Присоединиться", callback_data="zar_join")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def zars_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if dice_games.pop(chat_id, None) is not None:
        text = "🛑 Zar oyunu durduruldu.\n🛑 Игра в кости остановлена."
    else:
        text = "Aktif zar oyunu yok.\nНет активной игры в кости."
    await update.message.reply_text(text)


async def zar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    game = dice_games.get(chat_id)
    user = query.from_user
    name = user.first_name or user.username or "Oyuncu"

    if game is None:
        await query.answer(
            "Aktif oyun yok, /zar ile başlat.\nНет активной игры, начни с /zar.",
            show_alert=True,
        )
        return

    if query.data == "zar_join":
        if len(game["players"]) >= 2:
            await query.answer("Oyun zaten dolu.\nИгра уже заполнена.", show_alert=True)
            return
        if user.id == game["players"][0][0]:
            await query.answer("Zaten oyundasın.\nТы уже в игре.", show_alert=True)
            return

        game["players"].append((user.id, name))
        game["positions"][user.id] = 0
        game["started"] = True
        await query.answer("Katıldın!\nТы присоединился(лась)!")

        # Artık gerek kalmayan "Katıl" butonunu kaldır.
        await query.edit_message_reply_markup(reply_markup=None)

        current_id, current_name = game["players"][game["turn"]]
        text = (
            f"✅ Oyun başladı! Sıra sende, {current_name}\n"
            f"✅ Игра началась! Твой ход, {current_name}"
        )
        keyboard = [[InlineKeyboardButton("🎲 Zar at / Бросить кости", callback_data="zar_roll")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data == "zar_roll":
        if not game.get("started"):
            await query.answer(
                "Önce ikinci oyuncu katılmalı.\nСначала должен присоединиться второй игрок.",
                show_alert=True,
            )
            return

        current_id, current_name = game["players"][game["turn"]]
        if user.id != current_id:
            await query.answer("Sıra sende değil.\nСейчас не твой ход.", show_alert=True)
            return

        # Aynı anda iki kere basılırsa ikinci isteği görmezden gel (çakışmayı önler).
        if game.get("rolling"):
            await query.answer("Zar zaten atılıyor, bekle.\nКости уже брошены, подожди.")
            return
        game["rolling"] = True

        await query.answer()

        # Bu tur için kullanılan butonu kaldır, tekrar tıklanmasın.
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            dice_message = await context.bot.send_dice(chat_id=chat_id, emoji="🎲")
            value = dice_message.dice.value
            await asyncio.sleep(3.5)
        except Exception:
            # İnternet/bağlantı hatası: kilidi aç, oyuncu tekrar deneyebilsin.
            logger.exception("Zar atılırken bağlantı hatası")
            game["rolling"] = False
            keyboard = [[InlineKeyboardButton("🎲 Zar at / Бросить кости", callback_data="zar_roll")]]
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ Bağlantı sorunu oldu, zar atılamadı. Tekrar dene.\n"
                        "⚠️ Проблема с соединением, кости не брошены. Попробуй снова."
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            except Exception:
                pass
            return

        game["positions"][user.id] += value
        pos = game["positions"][user.id]

        if pos >= DICE_BOARD_LEN:
            text = (
                f"🏁 {current_name} {value} attı ve bitişe ulaştı!\n"
                f"🏆 Kazanan: {current_name}\n\n"
                f"🏁 {current_name} выбросил(а) {value} и дошёл(шла) до финиша!\n"
                f"🏆 Победитель: {current_name}"
            )
            await context.bot.send_message(chat_id=chat_id, text=text)
            dice_games.pop(chat_id, None)
            return

        # Küçük ihtimalle bir "yaratık" oyuncuyu rastgele bir kata taşır.
        creature_text = ""
        if random.random() < 0.15:
            new_pos = random.randint(0, DICE_BOARD_LEN - 1)
            if new_pos > pos:
                creature_text = (
                    f"\n\n🐉 Bir yaratık seni {pos}. kattan {new_pos}. kata çıkardı!\n"
                    f"🐉 Существо подняло тебя с этажа {pos} на {new_pos}!"
                )
            elif new_pos < pos:
                creature_text = (
                    f"\n\n👻 Bir yaratık seni {pos}. kattan {new_pos}. kata sürükledi!\n"
                    f"👻 Существо утащило тебя с этажа {pos} на {new_pos}!"
                )
            game["positions"][user.id] = new_pos
            pos = new_pos

        game["turn"] = 1 - game["turn"]
        game["rolling"] = False
        next_id, next_name = game["players"][game["turn"]]
        text = (
            f"🎲 {current_name}: {value} attı, konum {pos}/{DICE_BOARD_LEN}\n"
            f"🎲 {current_name}: выбросил(а) {value}, позиция {pos}/{DICE_BOARD_LEN}"
            f"{creature_text}\n\n"
            f"Sıra sende, {next_name}!\n"
            f"Твой ход, {next_name}!"
        )
        keyboard = [[InlineKeyboardButton("🎲 Zar at / Бросить кости", callback_data="zar_roll")]]
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            logger.exception("Sonuç mesajı gönderilirken bağlantı hatası")
            game["rolling"] = False


# ------------------ Kelime Oyunu / Игра в слова ------------------
# Sadece net, tartışmasız çevirisi olan kelimeler seçildi (yanlış öğrenilmesin diye).
WORD_PAIRS = [
    ("elma", "яблоко"),
    ("su", "вода"),
    ("ev", "дом"),
    ("kedi", "кошка"),
    ("köpek", "собака"),
    ("kitap", "книга"),
    ("aşk", "любовь"),
    ("güneş", "солнце"),
    ("deniz", "море"),
    ("dağ", "гора"),
    ("ağaç", "дерево"),
    ("çiçek", "цветок"),
    ("kuş", "птица"),
    ("balık", "рыба"),
    ("süt", "молоко"),
    ("ekmek", "хлеб"),
    ("kahve", "кофе"),
    ("çay", "чай"),
    ("okul", "школа"),
    ("araba", "машина"),
    ("şehir", "город"),
    ("arkadaş", "друг"),
    ("aile", "семья"),
    ("gün", "день"),
    ("gece", "ночь"),
    ("yıldız", "звезда"),
    ("güzel", "красивый"),
    ("büyük", "большой"),
    ("küçük", "маленький"),
    ("evet", "да"),
    ("hayır", "нет"),
    ("teşekkürler", "спасибо"),
]

# chat_id -> {"correct_index": int, "options": [str, str, str]}
kelime_games: dict[int, dict] = {}


async def send_kelime_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    tr, ru = random.choice(WORD_PAIRS)
    ask_ru_to_tr = random.random() < 0.5

    if ask_ru_to_tr:
        correct_answer = tr
        header = (
            f'🇷🇺 "{ru}" kelimesi Türkçe\'de ne demek?\n'
            f'🇷🇺 Что значит слово "{ru}" по-турецки?'
        )
        pool = [pair[0] for pair in WORD_PAIRS if pair[0] != correct_answer]
    else:
        correct_answer = ru
        header = (
            f'🇹🇷 "{tr}" kelimesi Rusça\'da ne demek?\n'
            f'🇹🇷 Что значит слово "{tr}" по-русски?'
        )
        pool = [pair[1] for pair in WORD_PAIRS if pair[1] != correct_answer]

    wrong_answers = random.sample(pool, 2)
    options = [correct_answer] + wrong_answers
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    kelime_games[chat_id] = {"correct_index": correct_index, "options": options}

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"kelime_{i}") for i, opt in enumerate(options)]
    ]
    try:
        await context.bot.send_message(
            chat_id=chat_id, text=header, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        logger.exception("Kelime sorusu gönderilirken hata")


async def kelime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        "📚 Kelime oyunu başladı! Doğru cevaba tıkla.\n"
        "📚 Игра в слова началась! Нажми на правильный ответ."
    )
    await send_kelime_question(chat_id, context)


async def kelimes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if kelime_games.pop(chat_id, None) is not None:
        text = "🛑 Kelime oyunu durduruldu.\n🛑 Игра в слова остановлена."
    else:
        text = "Aktif kelime oyunu yok.\nНет активной игры в слова."
    await update.message.reply_text(text)


async def kelime_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    game = kelime_games.get(chat_id)

    if game is None:
        await query.answer(
            "Aktif oyun yok, /kelime ile başlat.\nНет активной игры, начни с /kelime.",
            show_alert=True,
        )
        return

    chosen_index = int(query.data.replace("kelime_", ""))
    correct_index = game["correct_index"]
    options = game["options"]

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    if chosen_index == correct_index:
        await query.answer("Doğru! 🎉\nПравильно! 🎉")
    else:
        await query.answer(
            f"Yanlış. Doğrusu: {options[correct_index]}\n"
            f"Неправильно. Правильный ответ: {options[correct_index]}",
            show_alert=True,
        )

    if chat_id in kelime_games:
        await send_kelime_question(chat_id, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Beklenmeyen bir hata olursa bot çökmesin, sadece kaydedip devam etsin.
    logger.exception("Beklenmeyen hata: %s", context.error)


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("kalem", tkm_command))
    app.add_handler(CommandHandler("kalems", kalems_command))
    app.add_handler(CommandHandler("zar", zar_command))
    app.add_handler(CommandHandler("zars", zars_command))
    app.add_handler(CommandHandler("kosti", zar_command))
    app.add_handler(CommandHandler("kostistop", zars_command))
    app.add_handler(CommandHandler("kelime", kelime_command))
    app.add_handler(CommandHandler("kelimes", kelimes_command))
    app.add_handler(CallbackQueryHandler(tkm_callback, pattern="^tkm_"))
    app.add_handler(CallbackQueryHandler(zar_callback, pattern="^zar_"))
    app.add_handler(CallbackQueryHandler(kelime_callback, pattern="^kelime_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("Bot başlatıldı, mesajlar dinleniyor...")
    # drop_pending_updates: bot kapalıyken biriken eski mesajları yok sayar,
    # açılışta "spam çeviri" yapmasını engeller.
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
