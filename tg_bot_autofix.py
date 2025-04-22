
import logging
import os
import uuid
import re
import json
import subprocess
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TG_BOT_TOKEN")

HASHTAG_FILE = "video_hashtags.json"
USER_TAGS_FILE = "user_tags.json"
SUBSCRIBERS_FILE = "subscribers.json"

PREDEFINED_TAGS = ["#صحة", "#إسلام", "#تعليم", "#تقنية", "#ترفيه"]

OWNER_USERNAME = "ehabjobs"
OWNER_ID = 2169669

def is_subscribed(user_id, username=None):
    if username == OWNER_USERNAME or user_id == OWNER_ID:
        return True
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return str(user_id) in data
    return False

def set_subscribed(user_id):
    data = {}
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[str(user_id)] = True
    with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_filename(info_dict):
    title = info_dict.get('title', 'downloaded')
    title = re.sub(r'[^\w\-_\. ]', '_', title)
    return title[:50]

def save_video_tags(video_id, tags):
    data = {}
    if os.path.exists(HASHTAG_FILE):
        with open(HASHTAG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[video_id] = tags
    with open(HASHTAG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_tags(user_id):
    if os.path.exists(USER_TAGS_FILE):
        with open(USER_TAGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    return data.get(str(user_id), PREDEFINED_TAGS)

def save_user_tags(user_id, tags):
    data = {}
    if os.path.exists(USER_TAGS_FILE):
        with open(USER_TAGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[str(user_id)] = tags
    with open(USER_TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def rotate_video(filename):
    rotated_file = f"rotated_{filename}"
    cmd = [
        "ffmpeg", "-i", filename,
        "-vf", "transpose=1",
        "-c:a", "copy",
        rotated_file
    ]
    subprocess.run(cmd, check=True)
    os.replace(rotated_file, filename)

async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    if not url:
        await update.message.reply_text("❌ الرجاء إرسال رابط صحيح.")
        return

    if not is_subscribed(user_id, username):
        await update.message.reply_text("⭐ للاستخدام الكامل، الرجاء إرسال نجمة للبوت للاشتراك.")
        return

    try:
        info_dict = yt_dlp.YoutubeDL({"quiet": True}).extract_info(url, download=False)
        base_filename = extract_filename(info_dict)
        video_id = info_dict.get("id") or str(uuid.uuid4())

        hashtags = []
        description = info_dict.get('description', '')
        found_tags = re.findall(r'#\w+', description)
        if found_tags:
            hashtags = found_tags[:3]

        caption = base_filename
        if hashtags:
            caption += "\n" + " ".join(hashtags)

        video_filename = f"{uuid.uuid4()}_{base_filename}.mp4"
        audio_filename = f"{uuid.uuid4()}_{base_filename}.m4a"

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': video_filename,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(video_filename):
            await rotate_video(video_filename)
            with open(video_filename, 'rb') as f:
                await update.message.reply_video(video=f, filename=video_filename, caption=caption, supports_streaming=True)

        audio_extract_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_filename,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(audio_extract_opts) as ydl:
            ydl.download([url])

        if os.path.exists(audio_filename):
            with open(audio_filename, 'rb') as f:
                await update.message.reply_audio(audio=f, filename=audio_filename, caption=caption)

        user_tags = get_user_tags(update.message.from_user.id)
        keyboard = [[InlineKeyboardButton(tag, callback_data=f"tag|{video_id}|{tag}") for tag in user_tags[i:i+2]] for i in range(0, len(user_tags), 2)]
        keyboard.append([InlineKeyboardButton("✏️ تخصيص التصنيفات", callback_data=f"edit_tags|{video_id}")])
        await update.message.reply_text("📌 اختر تصنيف للفيديو:", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.exception("Download error:")
        await update.message.reply_text(f"❌ حدث خطأ أثناء التحميل: {str(e)}")

    finally:
        for file in [video_filename, audio_filename]:
            if os.path.exists(file):
                os.remove(file)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    if data[0] == "tag":
        video_id, tag = data[1], data[2]
        save_video_tags(video_id, [tag])
        await query.edit_message_text(f"✅ تم حفظ التصنيف: {tag}")

    elif data[0] == "edit_tags":
        await query.edit_message_text("🔧 أرسل التصنيفات الجديدة مفصولة بفواصل، مثل: #رياضة,#فن,#سفر")
        context.user_data['editing_tags'] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "⭐":
        set_subscribed(user_id)
        await update.message.reply_text("✅ تم تفعيل اشتراكك بنجاح!")
        return

    if context.user_data.get('editing_tags'):
        new_tags = [t.strip() for t in text.split(',') if t.strip()]
        if new_tags:
            save_user_tags(user_id, new_tags)
            await update.message.reply_text("✅ تم تحديث التصنيفات الخاصة بك.")
        else:
            await update.message.reply_text("❌ لم يتم التعرف على أي تصنيفات.")
        context.user_data['editing_tags'] = False
    else:
        await download_and_send(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 مرحباً! فقط أرسل رابط الفيديو، وسأقوم تلقائياً بتحميل الفيديو وإرسال ملف صوتي مرفق به. أرسل ⭐ للاشتراك.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()

if __name__ == '__main__':
    main()
