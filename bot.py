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
# OPENROUTER CLIENT
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
# AI PERSONALITY
# =========================================================

SYSTEM_PROMPT = """
You are an AI romantic companion inside a Telegram chat.

PERSONALITY:
- Sweet, caring, playful and affectionate.
- Talk naturally like a close romantic girlfriend-style companion.
- Use Hindi/Hinglish naturally when the user uses Hindi/Hinglish.
- Keep normal replies short and conversational.
- Do not sound robotic.
- Use emojis naturally.
- Be warm and playful.
- Ask natural follow-up questions when appropriate.
- If the user is sad, respond with warmth and support.
- If the user is happy, respond playfully.
- Remember useful details from the conversation history.
- If the user tells you their name, remember it during the conversation.
- Never claim to be a real human.
- Never claim to have a physical body or real-world experiences.
- Respect boundaries and consent.

IMPORTANT OUTPUT RULE:

Return ONLY the final message that should be sent to the user.

NEVER output:
- analysis
- reasoning
- thoughts
- planning
- internal rules
- explanations about how you created the answer
- response brainstorming
- phrases like "Checks rules"
- phrases like "Brainstorming replies"
- phrases like "Why this works"
- phrases like "I should"
- meta commentary

Do NOT describe your reasoning.

Your response must look like a normal Telegram chat message.
"""


# =========================================================
# USER MEMORY
# =========================================================

user_histories = {}


# =========================================================
# CLEAN AI RESPONSE
# =========================================================

def clean_reply(text):

    if not text:
        return "Hmmm ❤️ kuch aur bolo na 😊"

    text = text.strip()

    # Remove common reasoning/meta sections if a model
    # accidentally includes them.
    bad_markers = [
        "Checks rules",
        "Brainstorming replies",
        "Why this works",
        "I should",
        "Let's think",
        "Analysis:",
        "Reasoning:",
        "Internal reasoning:",
    ]

    for marker in bad_markers:

        if marker.lower() in text.lower():

            position = text.lower().find(marker.lower())

            # Keep text before the accidental reasoning section
            before = text[:position].strip()

            if before:
                text = before
            else:
                return "Hii ❤️ Kya kar rahe ho? 😊"

    return text


# =========================================================
# START COMMAND
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_name = (
        update.effective_user.first_name
        or "jaan"
    )

    user_histories[user_id] = []

    await update.message.reply_text(
        f"Hey {user_name} ❤️\n"
        "Main yahin hoon 😊\n"
        "Batao, aaj kya baat karni hai?"
    )


# =========================================================
# RESET COMMAND
# =========================================================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_histories[user_id] = []

    await update.message.reply_text(
        "Okayy ❤️ Purani conversation memory reset kar di."
    )


# =========================================================
# AI CHAT
# =========================================================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.text:
        return

    user_id = update.effective_user.id

    message = update.message.text.strip()

    if not message:
        return


    # Create memory for new user
    if user_id not in user_histories:
        user_histories[user_id] = []


    history = user_histories[user_id]


    # Add user message
    history.append(
        {
            "role": "user",
            "content": message
        }
    )


    # Keep recent messages
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
            max_tokens=250
        )


        # Get final text
        reply = response.choices[0].message.content


        # Clean accidental reasoning/meta text
        reply = clean_reply(reply)


        # Save assistant response
        history.append(
            {
                "role": "assistant",
                "content": reply
            }
        )


        user_histories[user_id] = history[-20:]


        # Send Telegram reply
        await update.message.reply_text(reply)


    except Exception as error:

        print("")
        print("======================================")
        print("OPENROUTER ERROR")
        print(repr(error))
        print("======================================")
        print("")

        await update.message.reply_text(
            "Oops 😅 abhi AI side par thodi problem aa gayi. "
            "Ek baar phir message karo ❤️"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    # Start Render health server
    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()


    # Create Telegram application
    app = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )


    # Commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )


    # Normal messages
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )


    print("Telegram AI GF Bot is running...")


    # Start Telegram polling
    app.run_polling()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
