import os
import logging
import requests
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import uvicorn

# ------------------ تنظیم لاگ ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ خواندن توکن و وبهوک ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("توکن ربات پیدا نشد! لطفاً BOT_TOKEN را در Environment Variables ست کن.")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("وبهوک پیدا نشد! لطفاً WEBHOOK_URL را در Environment Variables ست کن.")

PORT = int(os.getenv("PORT", 8000))

# ------------------ ساخت ربات و FastAPI ------------------
bot = Bot(BOT_TOKEN)
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# ------------------ /start command ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋 لینک ویدیو یا عکس اینستاگرام رو بفرست تا برات دانلود کنم."
    )

# ------------------ هندل کردن پیام ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        await update.message.reply_text("لطفاً لینک معتبر اینستاگرام بفرست 🚀")
        return

    try:
        api_url = f"https://api.snapinsta.app/api.php?url={text}"
        res = requests.get(api_url).json()

        if "url" in res:
            video_url = res["url"]
            await update.message.reply_video(video=video_url, caption="اینجا ویدیوت 🎥")
        else:
            await update.message.reply_text(
                "نتونستم دانلود کنم 😔 دوباره تلاش کن یا لینک دیگه بفرست."
            )
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("خطا در دانلود ویدیو ❌")

# ------------------ اضافه کردن هندلرها ------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ------------------ مسیر وبهوک ------------------
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}

# ------------------ ست کردن وبهوک در startup ------------------
@app.on_event("startup")
async def startup_event():
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logger.info("Webhook set successfully.")

# ------------------ اجرای uvicorn ------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
