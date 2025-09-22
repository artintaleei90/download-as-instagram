import os
import httpx
from urllib.parse import urlparse, unquote
from pathlib import Path

from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------
# تنظیمات
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://download-as-instagram.onrender.com")
PORT = int(os.getenv("PORT", 8000))

# Instagram App
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")
IG_REDIRECT_URI = os.getenv("IG_REDIRECT_URI", f"{WEBHOOK_URL}/ig_auth")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN تنظیم نشده!")

bot = Bot(BOT_TOKEN)
app = FastAPI()
application = Application.builder().token(BOT_TOKEN).build()

# حافظه‌ی موقت برای توکن کاربران
tokens_store = {}

# -------------------
# دستورات تلگرام

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام ✌️\n"
        "برای اتصال اینستاگرام دستور /login_ig رو بزن.\n"
        "بعدش می‌تونی با /get_url <لینک پست> فایل رو بگیری."
    )

application.add_handler(CommandHandler("start", start))

async def login_ig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    url = (
        f"https://api.instagram.com/oauth/authorize"
        f"?client_id={IG_APP_ID}"
        f"&redirect_uri={IG_REDIRECT_URI}"
        f"&scope=user_profile,user_media"
        f"&response_type=code"
        f"&state={chat_id}"
    )
    await update.message.reply_text(f"برای اتصال روی لینک زیر بزن:\n{url}")

application.add_handler(CommandHandler("login_ig", login_ig))

async def get_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id not in tokens_store:
        await update.message.reply_text("اول باید /login_ig رو اجرا کنی.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /get_url <instagram_post_url>")
        return

    url = unquote(context.args[0].strip())
    p = urlparse(url)
    parts = [seg for seg in p.path.split("/") if seg]
    shortcode = parts[1] if len(parts) >= 2 else parts[0]

    access_token = tokens_store[chat_id]["access_token"]

    # گرفتن مدیاهای کاربر
    media_url = (
        f"https://graph.instagram.com/me/media"
        f"?fields=id,media_type,media_url,thumbnail_url,permalink"
        f"&access_token={access_token}&limit=50"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(media_url)
    data = resp.json().get("data", [])

    found = None
    for item in data:
        if shortcode in item.get("permalink", ""):
            found = item
            break

    if not found:
        await update.message.reply_text("❌ پست مربوط به این حساب پیدا نشد.")
        return

    mtype = found.get("media_type")
    media_file_url = found.get("media_url") or found.get("thumbnail_url")

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(media_file_url)
    ext = ".jpg" if mtype == "IMAGE" else ".mp4"
    tmp_path = Path(f"/tmp/{found['id']}{ext}")
    tmp_path.write_bytes(r.content)

    if mtype == "IMAGE":
        await bot.send_photo(chat_id=update.effective_chat.id, photo=open(tmp_path, "rb"))
    elif mtype == "VIDEO":
        await bot.send_video(chat_id=update.effective_chat.id, video=open(tmp_path, "rb"))
    else:
        await bot.send_document(chat_id=update.effective_chat.id, document=open(tmp_path, "rb"))

application.add_handler(CommandHandler("get_url", get_url))

# -------------------
# Instagram OAuth callback
@app.get("/ig_auth")
async def ig_auth(code: str, state: str):
    # تبادل code با access_token
    token_url = "https://api.instagram.com/oauth/access_token"
    data = {
        "client_id": IG_APP_ID,
        "client_secret": IG_APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": IG_REDIRECT_URI,
        "code": code,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(token_url, data=data)
    res = resp.json()
    access_token = res.get("access_token")
    if not access_token:
        return {"error": res}

    tokens_store[state] = {"access_token": access_token}
    return {"status": "ok", "chat_id": state}

# -------------------
# FastAPI endpoints
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    # تنظیم وبهوک
    await bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

