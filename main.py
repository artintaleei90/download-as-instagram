import os
import logging
import requests
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("8274514106:AAFb4cTiB7eSqUlIHQQBGzK4YUTyNpsCRqo")  # توکن ربات تلگرام
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://download-as-instagram.onrender.com")
PORT = int(os.getenv("PORT", 8000))

bot = Bot(BOT_TOKEN)
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 لینک ویدیو یا عکس اینستاگرام رو بفرست تا برات دانلود کنم.")


# گرفتن لینک ویدیو از کاربر
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        await update.message.reply_text("لطفاً لینک معتبر اینستاگرام بفرست 🚀")
        return

    try:
        # استفاده از snapinsta.app به عنوان واسط
        api_url = f"https://api.snapinsta.app/api.php?url={text}"
        res = requests.get(api_url).json()

        if "url" in res:
            video_url = res["url"]
            await update.message.reply_video(video=video_url, caption="اینجا ویدیوت 🎥")
        else:
            await update.message.reply_text("نتونستم دانلود کنم 😔 دوباره تلاش کن یا لینک دیگه بفرست.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("خطا در دانلود ویدیو ❌")


# هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}


@app.on_event("startup")
async def startup_event():
    # ست کردن webhook روی تلگرام
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logger.info("Webhook set.")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
