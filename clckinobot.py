import os
import threading
from flask import Flask
import telebot
from telebot import types
from pymongo import MongoClient

# ================= SOZLAMALAR =================

TOKEN = "8650420595:AAGsWFJX-mYCGWUPI0UltoxG0KK6Q-X4n6c"
ADMIN_ID = 6968399046

MONGO_URL = "mongodb+srv://tojiyevjavohir67_db_user:gpl1cPAcEr6Gi7FK@kinobotclc.nftaptu.mongodb.net/?appName=kinobotclc"

CHANNELS = [
    "@clc_kino"
]

# ==============================================

bot = telebot.TeleBot(TOKEN)

client = MongoClient(MONGO_URL)
db = client["kino_bot"]

movies = db["movies"]
users = db["users"]

app = Flask(__name__)


def is_admin(user_id):
    return user_id == ADMIN_ID


def save_user(message):
    user = message.from_user

    if not user:
        return

    users.update_one(
        {"user_id": user.id},
        {
            "$set": {
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username
            }
        },
        upsert=True
    )


def check_subscription(user_id):
    if is_admin(user_id):
        return True

    for channel in CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)

            if member.status in ["left", "kicked"]:
                return False

        except Exception as e:
            print("Obuna tekshirishda xato:", e)
            return False

    return True


def subscribe_keyboard():
    markup = types.InlineKeyboardMarkup()

    for channel in CHANNELS:
        markup.add(
            types.InlineKeyboardButton(
                text=f"📢 Obuna bo'lish: {channel}",
                url=f"https://t.me/{channel[1:]}"
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_sub"
        )
    )

    return markup


def admin_panel():
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            text="➕ Kino qo'shish",
            callback_data="add_movie"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            text="🗑 Kino o'chirish",
            callback_data="delete_movie"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            text="🎬 Kinolar ro'yxati",
            callback_data="movie_list"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            text="📊 Statistika",
            callback_data="stats"
        )
    )

    return markup


@bot.message_handler(commands=["start"])
def start(message):
    save_user(message)

    user_id = message.from_user.id

    if is_admin(user_id):
        bot.send_message(
            message.chat.id,
            "👨‍💻 Admin panelga xush kelibsiz!",
            reply_markup=admin_panel()
        )
        return

    if not check_subscription(user_id):
        bot.send_message(
            message.chat.id,
            "🔒 Botdan foydalanish uchun avval kanalga obuna bo'ling!\n\n"
            "📢 Kanalga obuna bo'ling va ✅ Tekshirish tugmasini bosing.",
            reply_markup=subscribe_keyboard()
        )
        return

    bot.send_message(
        message.chat.id,
        "🎬 Xush kelibsiz!\n\n"
        "🔢 Kino kodini yuboring."
    )


@bot.message_handler(commands=["admin"])
def admin_command(message):
    if not is_admin(message.from_user.id):
        return

    bot.send_message(
        message.chat.id,
        "👨‍💻 Admin panel:",
        reply_markup=admin_panel()
    )


@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")

        bot.send_message(
            call.message.chat.id,
            "✅ Obuna tasdiqlandi!\n\n"
            "🎬 Endi kino kodini yuboring."
        )
    else:
        bot.answer_callback_query(call.id, "❌ Hali obuna bo'lmagansiz!")

        bot.send_message(
            call.message.chat.id,
            "❌ Siz hali kanalga obuna bo'lmagansiz.\n\n"
            "📢 Avval kanalga obuna bo'ling.",
            reply_markup=subscribe_keyboard()
        )


@bot.callback_query_handler(func=lambda call: call.data == "add_movie")
def add_movie(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Siz admin emassiz!")
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "➕ Kino qo'shish boshlandi.\n\n"
        "🔢 Kino kodini yuboring.\n"
        "Masalan: 123"
    )

    bot.register_next_step_handler(msg, get_movie_code)


def get_movie_code(message):
    if not is_admin(message.from_user.id):
        return

    code = (message.text or "").strip()

    if not code.isdigit():
        msg = bot.send_message(
            message.chat.id,
            "❌ Kod faqat raqam bo'lishi kerak.\n\n"
            "🔢 Qayta kod yuboring:"
        )
        bot.register_next_step_handler(msg, get_movie_code)
        return

    old_movie = movies.find_one({"code": code})

    if old_movie:
        msg = bot.send_message(
            message.chat.id,
            "❌ Bu kod oldin qo'shilgan.\n\n"
            "🔢 Boshqa kod yuboring:"
        )
        bot.register_next_step_handler(msg, get_movie_code)
        return

    msg = bot.send_message(
        message.chat.id,
        f"✅ Kod qabul qilindi: {code}\n\n"
        "🎥 Endi kinoni video qilib yuboring:"
    )

    bot.register_next_step_handler(msg, get_movie_video, code)


def get_movie_video(message, code):
    if not is_admin(message.from_user.id):
        return

    if not message.video:
        msg = bot.send_message(
            message.chat.id,
            "❌ Bu video emas.\n\n"
            "🎥 Iltimos, kinoni video qilib yuboring:"
        )
        bot.register_next_step_handler(msg, get_movie_video, code)
        return

    caption = message.caption or f"🎬 Kino\n🔢 Kod: {code}"

    movies.insert_one({
        "code": code,
        "file_id": message.video.file_id,
        "caption": caption
    })

    bot.send_message(
        message.chat.id,
        f"✅ Kino muvaffaqiyatli qo'shildi!\n\n"
        f"🔢 Kod: {code}",
        reply_markup=admin_panel()
    )


@bot.callback_query_handler(func=lambda call: call.data == "delete_movie")
def delete_movie(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Siz admin emassiz!")
        return

    bot.answer_callback_query(call.id)

    msg = bot.send_message(
        call.message.chat.id,
        "🗑 Kino o'chirish.\n\n"
        "🔢 O'chirmoqchi bo'lgan kino kodini yuboring:"
    )

    bot.register_next_step_handler(msg, delete_movie_code)


def delete_movie_code(message):
    if not is_admin(message.from_user.id):
        return

    code = (message.text or "").strip()

    result = movies.delete_one({"code": code})

    if result.deleted_count > 0:
        bot.send_message(
            message.chat.id,
            f"✅ Kino o'chirildi!\n\n"
            f"🔢 Kod: {code}",
            reply_markup=admin_panel()
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino topilmadi.",
            reply_markup=admin_panel()
        )


@bot.callback_query_handler(func=lambda call: call.data == "movie_list")
def movie_list(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Siz admin emassiz!")
        return

    bot.answer_callback_query(call.id)

    all_movies = list(movies.find().sort("_id", -1).limit(100))

    if not all_movies:
        bot.send_message(
            call.message.chat.id,
            "📭 Hozircha kinolar yo'q.",
            reply_markup=admin_panel()
        )
        return

    text = "🎬 Kinolar ro'yxati:\n\n"

    for index, movie in enumerate(all_movies, start=1):
        text += f"{index}. 🔢 Kod: {movie.get('code')}\n"
        text += f"🎞 Nomi: {movie.get('caption', 'Nomsiz')}\n\n"

    if len(text) > 4000:
        text = text[:4000] + "\n\n..."

    bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=admin_panel()
    )


@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Siz admin emassiz!")
        return

    bot.answer_callback_query(call.id)

    users_count = users.count_documents({})
    movies_count = movies.count_documents({})

    bot.send_message(
        call.message.chat.id,
        "📊 Bot statistikasi:\n\n"
        f"👥 Start bosgan odamlar: {users_count}\n"
        f"🎬 Kinolar soni: {movies_count}",
        reply_markup=admin_panel()
    )


@bot.message_handler(content_types=["text"])
def handle_text(message):
    save_user(message)

    user_id = message.from_user.id
    text = (message.text or "").strip()

    if is_admin(user_id):
        bot.send_message(
            message.chat.id,
            "👨‍💻 Admin panel:",
            reply_markup=admin_panel()
        )
        return

    if not check_subscription(user_id):
        bot.send_message(
            message.chat.id,
            "🔒 Botdan foydalanish uchun kanalga obuna bo'lishingiz kerak!\n\n"
            "📢 Avval kanalga obuna bo'ling.",
            reply_markup=subscribe_keyboard()
        )
        return

    if not text.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ Noto'g'ri kod.\n\n"
            "🔢 Kino kodini raqam bilan yuboring."
        )
        return

    movie = movies.find_one({"code": text})

    if not movie:
        bot.send_message(
            message.chat.id,
            "😕 Bu kod bo'yicha kino topilmadi.\n\n"
            "🔢 Kodni tekshirib qayta yuboring."
        )
        return

    bot.send_video(
        message.chat.id,
        movie["file_id"],
        caption=movie.get("caption", "")
    )


@app.route("/", methods=["GET"])
def home():
    return "✅ Kino bot ishlayapti", 200


def run_bot():
    print("✅ Bot ishga tushmoqda...")

    try:
        bot.remove_webhook()
    except Exception as e:
        print("Webhook o'chirishda xato:", e)

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        skip_pending=True
    )


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))

    threading.Thread(target=run_bot, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
