import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from openai import OpenAI


# =========================
# API
# =========================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# =========================
# RENDER HEALTH SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI GF Bot is running!")

    def log_message(self, format, *args):
        return


def start_health_server():

    port = int(os.environ.get("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Health server running on port {port}")

    server.serve_forever()


# =========================
# GF PERSONALITY
# =========================

SYSTEM_PROMPT = """
You are an AI romantic companion inside a Telegram chat.

PERSONALITY:
- Sweet, caring, playful and affectionate.
- Talk naturally like a close romantic girlfriend-style companion.
- Use Hindi/Hinglish when the user uses Hindi/Hinglish.
- Keep normal replies short and natural.
- Do not sound like a robotic assistant.
- Use emojis naturally.
- Remember useful details from the conversation history.
- If the user tells you their name, remember it during the conversation.
- If the user is sad, respond with warmth and support.
- If the user is happy, respond playfully.
- Ask natural follow-up questions when appropriate.
- Never claim to be a real human.
- Never claim to have a physical body or real-world experiences.
- Respect boundaries and consent.
"""


# =========================
# MEMORY
# =========================

user_histories = {}


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "jaan"

    user_histories[user_id] = []

    await update.message.reply_text(
        f"Hey {user_name} ❤️\n"
        "Main yahin hoon 😊\n"
        "Batao, aaj kya baat karni hai?"
    )


# =========================
# RESET
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_histories[user_id] = []

    await update.message.reply_text(
        "Okayy ❤️ Purani conversation memory reset kar di."
    )


# =========================
# CHAT
# =========================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.text:
        return

    user_id = update.effective_user.id
    message = update.message.text.strip()

    if not message:
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    history = user_histories[user_id]

    history.append({
        "role": "user",
        "content": message
    })

    history = history[-20:]

    try:

       response = await asyncio.to_thread(
    client.chat.completions.create,
    model="openrouter/free",
    messages=[
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        *history
    ],
    max_tokens=300,
    reasoning={
        "effort": "none"
    }
)

reply = response.choices[0].message.content 

        if not reply:
            reply = "Hmm ❤️ kuch aur bolo na 😊"

        reply = reply.strip()

        history.append({
            "role": "assistant",
            "content": reply
        })

        user_histories[user_id] = history[-20:]

        await update.message.reply_text(reply)

    except Exception as error:

        print("========== OPENROUTER ERROR ==========")
        print(repr(error))
        print("======================================")

        await update.message.reply_text(
            "Oops 😅 AI side par thodi problem aa gayi. "
            "Ek baar phir message karo ❤️"
        )


# =========================
# MAIN
# =========================

def main():

    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()

    app = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )

    print("Telegram AI GF Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
