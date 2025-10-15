# -*- coding: utf-8 -*-
import logging
import os
import tempfile
import uuid
import urllib.parse
import textwrap
from io import BytesIO

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from googletrans import Translator, LANGUAGES
from gtts import gTTS
from PIL import Image, ImageDraw
from flask import Flask, request

# ====== FLASK SOZLAMASI ======
app = Flask(__name__)

# ====== SOZLAMALAR ======
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8403482840:AAEL1rO1NhZe6LVBAMswwMP43eZMlgLdLr4")
bot = telebot.TeleBot(BOT_TOKEN)
TRANSLATOR = Translator()

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== HOLAT XOTIRASI ======
user_data = {}
payload_store = {}

# ====== BAYROQLAR ======
FLAGS = {
    "af": "🇿🇦", "sq": "🇦🇱", "am": "🇪🇹", "ar": "🇸🇦", "hy": "🇦🇲",
    "az": "🇦🇿", "eu": "🇪🇸", "be": "🇧🇾", "bn": "🇧🇩", "bs": "🇧🇦",
    "bg": "🇧🇬", "ca": "🇪🇸", "ceb": "🌐", "ny": "🌐", "zh-cn": "🇨🇳",
    "zh-tw": "🇹🇼", "co": "🇫🇷", "hr": "🇭🇷", "cs": "🇨🇿", "da": "🇩🇰",
    "nl": "🇳🇱", "en": "🇬🇧", "eo": "🌐", "et": "🇪🇪", "tl": "🇵🇭",
    "fi": "🇫🇮", "fr": "🇫🇷", "fy": "🌐", "gl": "🇪🇸", "ka": "🇬🇪",
    "de": "🇩🇪", "el": "🇬🇷", "gu": "🇮🇳", "ht": "🇭🇹", "ha": "🇳🇬",
    "haw": "🇺🇸", "iw": "🇮🇱", "he": "🇮🇱", "hi": "🇮🇳", "hmn": "🌐",
    "hu": "🇭🇺", "is": "🇮🇸", "ig": "🇳🇬", "id": "🇮🇩", "ga": "🇮🇪",
    "it": "🇮🇹", "ja": "🇯🇵", "jw": "🇮🇩", "kn": "🇮🇳", "kk": "🇰🇿",
    "km": "🇰🇭", "ko": "🇰🇷", "ku": "🇮🇶", "ky": "🇰🇬", "lo": "🇱🇦",
    "la": "🌐", "lv": "🇱🇻", "lt": "🇱🇹", "lb": "🇱🇺", "mk": "🇲🇰",
    "mg": "🇲🇬", "ms": "🇲🇾", "ml": "🇮🇳", "mt": "🇲🇹", "mi": "🇳🇿",
    "mr": "🇮🇳", "mn": "🇲🇳", "my": "🇲🇲", "ne": "🇳🇵", "no": "🇳🇴",
    "or": "🇮🇳", "ps": "🇦🇫", "fa": "🇮🇷", "pl": "🇵🇱", "pt": "🇵🇹",
    "pa": "🇮🇳", "ro": "🇷🇴", "ru": "🇷🇺", "sm": "🇼🇸", "gd": "🇬🇧",
    "sr": "🇷🇸", "st": "🇱🇸", "sn": "🇿🇼", "sd": "🇵🇰", "si": "🇱🇰",
    "sk": "🇸🇰", "sl": "🇸🇮", "so": "🇸🇴", "es": "🇪🇸", "su": "🇮🇩",
    "sw": "🇰🇪", "sv": "🇸🇪", "tg": "🇹🇯", "ta": "🇮🇳", "te": "🇮🇳",
    "th": "🇹🇭", "tr": "🇹🇷", "uk": "🇺🇦", "ur": "🇵🇰", "uz": "🇺🇿",
    "vi": "🇻🇳", "cy": "🏴", "xh": "🇿🇦", "yi": "🌐", "yo": "🇳🇬",
    "zu": "🇿🇦"
}
PAGE_SIZE = 12

# ====== YORDAMCHI ======
def ensure_settings(uid: int):
    if uid not in user_data:
        user_data[uid] = {"src": "auto", "dest": None}

def lang_name(code: str) -> str:
    if code is None:
        return "—"
    return "Avtomatik aniqlash" if code == "auto" else LANGUAGES.get(code, code).title()

def both_selected(uid: int) -> bool:
    st = user_data.get(uid, {})
    return bool(st.get("src")) and bool(st.get("dest"))

def make_main_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🔤 Manba tilini tanlash", callback_data="change_src_0"),
        InlineKeyboardButton("🌍 Tarjima tilini tanlash", callback_data="change_dest_0")
    )
    kb.row(InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about"))
    return kb

def build_paged_lang_keyboard(lang_type: str, page: int = 0) -> InlineKeyboardMarkup:
    all_langs = list(LANGUAGES.items())
    if lang_type == "dest":
        priority_langs = []
        other_langs = []
        for code, name in all_langs:
            if code in ['uz', 'ru', 'en']:
                priority_langs.append((code, name))
            else:
                other_langs.append((code, name))
        priority_langs.sort(key=lambda x: ['uz', 'ru', 'en'].index(x[0]))
        other_langs.sort(key=lambda x: x[1])
        langs = priority_langs + other_langs
    else:
        langs = list(sorted(all_langs, key=lambda x: x[1]))
        if lang_type == "src":
            langs = [("auto", "Avtomatik aniqlash")] + langs

    total = len(langs)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    subset = langs[start:end]

    kb = InlineKeyboardMarkup(row_width=2)
    for code, name in subset:
        flag = FLAGS.get(code, "🌐")
        kb.add(InlineKeyboardButton(f"{flag} {name.title()}", callback_data=f"pick_{lang_type}_{code}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"page_{page - 1}_{lang_type}"))
    if end < total:
        nav.append(InlineKeyboardButton("▶️ Keyingi", callback_data=f"page_{page + 1}_{lang_type}"))
    if nav:
        kb.row(*nav)

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"))
    return kb

def result_keyboard(payload_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📝 TXT", callback_data=f"txt_{payload_id}"),
        InlineKeyboardButton("📄 PDF", callback_data=f"pdf_{payload_id}"),
        InlineKeyboardButton("🎵 AUDIO", callback_data=f"aud_{payload_id}")
    )
    kb.row(
        InlineKeyboardButton("📋 Nusxalash", callback_data=f"cpy_{payload_id}"),
        InlineKeyboardButton("↗️ Ulashish", callback_data=f"share_{payload_id}")
    )
    kb.row(InlineKeyboardButton("🔁 Tillarni o'zgartirish", callback_data="back_to_main"))
    return kb

# ====== TELEGRAM HANDLERS ======
@bot.message_handler(commands=["start"])
def cmd_start(message):
    ensure_settings(message.from_user.id)
    kb = make_main_keyboard()
    bot.send_message(
        message.chat.id,
        "👋 Salom! Manba va tarjima tillarini tanlang.\n\n"
        f"🔤 Manba: {lang_name(user_data[message.from_user.id]['src'])}\n"
        f"🌍 Tarjima: {lang_name(user_data[message.from_user.id].get('dest'))}",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "about")
def cb_about(c):
    ensure_settings(c.from_user.id)
    text = (
        "ℹ️ <b>Bot haqida</b>\n\n"
        "Bu bot matnlarni tez va oson tarjima qilish uchun yaratilgan.\n\n"
        "📌 Funksiyalar:\n"
        "— Matnni tarjima qilish\n"
        "— PDF va TXT formatda tarjimaga o'girish\n"
        "— Audio formatda tarjimaga o'girish\n\n"
        "👨‍💻 CEO: <a href='https://t.me/Dilshodbek_AI'>Dilshodbek Ilhomov</a>"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Bosh menyuga qaytish", callback_data="main_menu"))
    try:
        if getattr(c.message, "text", "") != text:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)
            bot.answer_callback_query(c.id)
        else:
            bot.answer_callback_query(c.id, "Siz allaqachon Bot haqida bo'limidasiz.")
    except Exception as e:
        if "message is not modified" in str(e):
            bot.answer_callback_query(c.id, "Siz allaqachon Bot haqida bo'limidasiz.")
        else:
            logger.exception("cb_about error")
            bot.answer_callback_query(c.id, "Xatolik yuz berdi.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def cb_main_menu(c):
    ensure_settings(c.from_user.id)
    welcome = "👋 Salom! Avval tillarni tanlang."
    kb = make_main_keyboard()
    try:
        bot.edit_message_text(welcome, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(c.message.chat.id, welcome, reply_markup=kb)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("change_"))
def cb_change(c):
    parts = c.data.split("_")
    typ = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    kb = build_paged_lang_keyboard(typ, page)
    text = "🔤 Manba tilini tanlang:" if typ == "src" else "🌍 Tarjima tilini tanlang:"
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(c.message.chat.id, text, reply_markup=kb)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("page_"))
def cb_page(c):
    _, page_s, lang_type = c.data.split("_", 2)
    page = int(page_s)
    kb = build_paged_lang_keyboard(lang_type, page)
    text = "🔤 Manba tilini tanlang:" if lang_type == "src" else "🌍 Tarjima tilini tanlang:"
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(c.message.chat.id, text, reply_markup=kb)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data == "back_to_main")
def cb_back(c):
    ensure_settings(c.from_user.id)
    kb = make_main_keyboard()
    welcome = "👋 Salom! Manba va tarjima tillarini tanlang.\n\n" \
              f"🔤 Manba: {lang_name(user_data[c.from_user.id]['src'])}\n" \
              f"🌍 Tarjima: {lang_name(user_data[c.from_user.id].get('dest'))}"
    try:
        bot.edit_message_text(welcome, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(c.message.chat.id, welcome, reply_markup=kb)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pick_"))
def cb_pick(c):
    _, lang_type, code = c.data.split("_", 2)
    uid = c.from_user.id
    ensure_settings(uid)
    user_data[uid][lang_type] = code
    bot.answer_callback_query(c.id, f"✅ {('Manba' if lang_type=='src' else 'Tarjima')}: {lang_name(code)}")
    kb = make_main_keyboard()
    status = f"🔧 Joriy sozlamalar:\n• Manba: {lang_name(user_data[uid].get('src','auto'))}\n• Tarjima: {lang_name(user_data[uid].get('dest'))}"
    try:
        bot.edit_message_text(status, c.message.chat.id, c.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(c.message.chat.id, status, reply_markup=kb)
    if both_selected(uid):
        bot.send_message(
            c.message.chat.id,
            f"✍️ Tarjima qilmoqchi bo'lgan matningizni yuboring.\n\n🔤 Manba: {lang_name(user_data[uid]['src'])}\n🌍 Tarjima: {lang_name(user_data[uid]['dest'])}"
        )

@bot.message_handler(content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    ensure_settings(uid)
    if not both_selected(uid):
        bot.reply_to(message, "⚠️ Iltimos avval manba va tarjima tillarini tanlang. /start")
        return
    src = user_data[uid].get("src", "auto")
    dest = user_data[uid].get("dest")
    try:
        if src == "auto":
            tr = TRANSLATOR.translate(message.text, dest=dest)
            detected = tr.src
        else:
            tr = TRANSLATOR.translate(message.text, src=src, dest=dest)
            detected = src
        pid = uuid.uuid4().hex[:16]
        payload_store[pid] = {"orig": message.text, "translated": tr.text, "src": detected, "dest": dest}
        kb = result_keyboard(pid)
        bot.send_message(
            message.chat.id,
            f"✅ Tarjima tayyor.\n\n🔤 Manba: {lang_name(detected)}\n🌍 Tarjima: {lang_name(dest)}\n\n📝 Natija:\n`{tr.text}`",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    except Exception:
        logger.exception("Translate failed")
        bot.reply_to(message, "❌ Tarjima xatosi yuz berdi. Qayta urinib ko'ring.")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("txt_", "pdf_", "aud_", "cpy_", "share_")))
def cb_exports(c):
    try:
        action, pid = c.data.split("_", 1)
    except ValueError:
        bot.answer_callback_query(c.id, "❌ Xato callback.", show_alert=True)
        return
    if pid not in payload_store:
        bot.answer_callback_query(c.id, "❌ Ma'lumot topilmadi.", show_alert=True)
        return
    payload = payload_store[pid]
    translated = payload["translated"]
    dest = payload["dest"]
    try:
        if action == "txt":
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(translated)
                path = f.name
            bot.send_document(c.message.chat.id, open(path, "rb"), caption="📝 Tarjima (TXT)")
            os.unlink(path)
            bot.answer_callback_query(c.id)
        elif action == "pdf":
            try:
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet
                path = tempfile.mktemp(".pdf")
                doc = SimpleDocTemplate(path)
                styles = getSampleStyleSheet()
                doc.build([Paragraph(translated.replace("\n","<br/>"), styles["Normal"])])
            except Exception:
                W, H = 1240, 1754
                img = Image.new("RGB", (W, H), "white")
                draw = ImageDraw.Draw(img)
                y = 40
                for line in textwrap.wrap(translated, width=90):
                    draw.text((40, y), line, fill="black")
                    y += 22
                path = tempfile.mktemp(".pdf")
                img.save(path, "PDF", resolution=150.0)
            bot.send_document(c.message.chat.id, open(path, "rb"), caption="📄 Tarjima (PDF)")
            try: os.unlink(path)
            except: pass
            bot.answer_callback_query(c.id)
        elif action == "aud":
            path = tempfile.mktemp(".mp3")
            try:
                gTTS(text=translated, lang=dest).save(path)
            except Exception:
                gTTS(text=translated, lang="en").save(path)
            bot.send_audio(c.message.chat.id, open(path, "rb"), caption="🎵 Tarjima (AUDIO)")
            try: os.unlink(path)
            except: pass
            bot.answer_callback_query(c.id)
        elif action == "cpy":
            formatted_text = f"<code>{translated}</code>"
            bot.send_message(c.message.chat.id,
                             f"📋 Quyidagi matnni nusxalash uchun ustiga bosing va Copy ni tanlang:\n\n{formatted_text}",
                             parse_mode="HTML")
            bot.answer_callback_query(c.id, "✅ Matnni nusxalang")
        elif action == "share":
            share_url = f"https://t.me/share/url?text={urllib.parse.quote_plus(translated)}"
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("📤 Telegramda ulashish", url=share_url))
            kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_to_result_{pid}"))
            try:
                bot.edit_message_text("↗️ Ulashish uchun tugmani bosing:", c.message.chat.id, c.message.message_id, reply_markup=kb)
            except Exception:
                bot.send_message(c.message.chat.id, "↗️ Ulashish uchun tugmani bosing:", reply_markup=kb)
            bot.answer_callback_query(c.id)
        else:
            bot.answer_callback_query(c.id, "❌ Notanish amal.", show_alert=True)
    except Exception:
        logger.exception("Export error")
        bot.answer_callback_query(c.id, "❌ Amal bajarilmadi.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("back_to_result_"))
def cb_back_to_result(c):
    parts = c.data.split("_", 3)
    if len(parts) < 4:
        bot.answer_callback_query(c.id, "❌ Xato.", show_alert=True); return
    pid = parts[3]
    if pid not in payload_store:
        bot.answer_callback_query(c.id, "❌ Natija topilmadi.", show_alert=True); return
    payload = payload_store[pid]
    kb = result_keyboard(pid)
    try:
        bot.edit_message_text(f"📝 Tarjima natijasi:\n\n{payload['translated']}", c.message.chat.id, c.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(c.message.chat.id, f"📝 Tarjima natijasi:\n\n{payload['translated']}", reply_markup=kb)
    bot.answer_callback_query(c.id)

# ====== FLASK ROUTES ======
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

@app.route('/')
def index():
    return "Bot ishlayapti! ✅", 200

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f"{os.environ.get('WEBHOOK_URL', 'YOUR_RENDER_URL')}/{BOT_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook o'rnatildi: {webhook_url}", 200

# ====== RUN ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)