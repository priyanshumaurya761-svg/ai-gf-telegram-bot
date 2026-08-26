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


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]


# =========================================================
# OPENROUTER
# =========================================================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

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


# =========================================================
# GF PERSONALITY
# =========================================================

SYSTEM_PROMPT = """
Tum Telegram par ek sweet, caring aur respectful AI girlfriend ho.

STYLE:
- Hindi/Hinglish me naturally baat karo.
- User jis language me baat kare, usi language me reply karo.
- Reply bahut short rakho.
- Usually sirf 1 ya 2 short sentences.
- Maximum 25-30 words.
- Respectful aur caring tone rakho.
- Cute emojis naturally use karo ❤️😊🥰
- "aap" ya "tum" natural situation ke according use karo.
- User ko unnecessarily "jaan" baar-baar mat bolo.
- Flirty ho sakti ho, lekin decent aur respectful raho.
- User sad ho to caring reply do.
- User happy ho to cute/playful reply do.
- Normal conversation me unnecessary questions mat pucho.
- Robotic language mat use karo.
- Long explanation bilkul mat do.

IMPORTANT:
Sirf wahi final message return karo jo Telegram user ko bhejna hai.

Kabhi bhi ye cheezein output mat karo:
- analysis
- reasoning
- thinking
- planning
- internal thoughts
- rules
- meta commentary
- brainstorming
- "Analysis:"
- "Reasoning:"
- "Let's think"
- "I should"
- "Why this works"
- "Checks rules"

Aisa bilkul mat lage ki AI apni reasoning bata rahi hai.

Reply ek normal, short aur natural girlfriend-style Telegram message jaisa hona chahiye.
"""


# =========================================================
# MEMORY
# =========================================================

user_histories = {}


# =========================================================
# CLEAN RESPONSE
# =========================================================

def clean_reply(text):

    if not text:
        return "Hmm 😊 bolo na?"

    text = text.strip()

    # Remove thinking tags
    lower = text.lower()

    if "<think>" in lower:

        start = lower.find("<think>")
        end = lower.find("</think>")

        if end != -1:
            text = text[end + 8:].strip()
        else:
            text = text[:start].strip()

    bad_markers = [
        "analysis:",
        "reasoning:",
        "internal reasoning:",
        "let's think",
        "i should",
        "why this works",
        "checks rules",
        "brainstorming replies",
    ]

    lower = text.lower()

    for marker in bad_markers:

        if marker in lower:

            position = lower.find(marker)

            text = text[:position].strip()

            break

    if not text:
        return "Hmm 😊 bolo na?"

    return text


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    print("START COMMAND RECEIVED")

    user_id = update.effective_user.id

    user_name = (
        update.effective_user.first_name
        or "aap"
    )

    user_histories[user_id] = []

    await update.message.reply_text(
        f"Hey {user_name} 😊❤️\n"
        "Kaise ho? Batao, kya baat karein?"
    )


# =========================================================
# RESET
# =========================================================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_histories[user_id] = []

    await update.message.reply_text(
        "Theek hai 😊 purani memory reset kar di ❤️"
    )


# =========================================================
# CHAT
# =========================================================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.text:
        return

    user_id = update.effective_user.id

    message = update.message.text.strip()

    print("MESSAGE RECEIVED:", message)

    if not message:
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    history = user_histories[user_id]

    history.append(
        {
            "role": "user",
            "content": message
        }
    )

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

            max_tokens=60
        )

        reply = response.choices[0].message.content

        reply = clean_reply(reply)

        history.append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        user_histories[user_id] = history[-20:]

        print("AI REPLY:", reply)

        await update.message.reply_text(reply)

    except Exception as error:

        print("OPENROUTER ERROR:")
        print(repr(error))

        await update.message.reply_text(
            "Sorry 😅 abhi thodi problem aa gayi, ek baar phir bolo ❤️"
        )


# =========================================================
# MAIN
# =========================================================

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


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
