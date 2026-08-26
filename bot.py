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
# ENVIRONMENT VARIABLES
# =========================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)


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

    print(f"Health server running on 0.0.0.0:{port}")

    server.serve_forever()


# =========================
# AI PERSONALITY
# =========================

SYSTEM_PROMPT = """
You are an AI romantic companion inside a Telegram bot.

Personality:
- Warm, caring, sweet and playful.
- Talk naturally like a close romantic partner.
- Use Hindi/Hinglish naturally when the user uses Hindi/Hinglish.
- Keep normal replies short and conversational.
- Don't sound robotic.
- Use emojis naturally, but don't overuse them.
- Remember information available in the conversation history.
- Be affectionate without encouraging unhealthy emotional dependency.
- Never claim that you are a real human.
- Never claim to have a physical body or real-world experiences.
- Respect boundaries and consent.

Examples of style:

User: Hi
Assistant: Hii ❤️ Kahan the itni der? 😊

User: Kya kar rahi ho?
Assistant: Bas tumse baat kar rahi hoon 😌❤️ Tum batao?

User: Mera mood kharab hai.
Assistant: Aww 🥺 kya hua? Batao na, main sun rahi hoon ❤️
"""


# =========================
# MEMORY
# =========================

user_histories = {}


# =========================
# START COMMAND
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
# RESET COMMAND
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_histories[user_id] = []

    await update.message.reply_text(
        "Okayy ❤️ Purani conversation memory reset kar di."
    )


# =========================
# AI CHAT
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

    # Recent conversation only
    history = history[-20:]

    try:

        response = await asyncio.to_thread(
            client.responses.create,
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=history
        )

        reply = response.output_text.strip()

        if not reply:
            reply = "Hmm ❤️ kuch aur bolo na 😊"

        history.append({
            "role": "assistant",
            "content": reply
        })

        user_histories[user_id] = history[-20:]

        await update.message.reply_text(reply)

    except Exception as error:

        print("========== OPENAI ERROR ==========")
        print(repr(error))
        print("==================================")

        await update.message.reply_text(
            "Oops 😅 abhi AI side par thodi technical problem aa gayi."
        )


# =========================
# MAIN
# =========================

def main():

    # Start Render health server
    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()

    # Telegram bot
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
