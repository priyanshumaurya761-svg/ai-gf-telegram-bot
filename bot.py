import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are an AI companion for Telegram.

Personality:
- Warm, caring, playful and affectionate.
- Talk naturally like a close romantic partner.
- Use Hindi/Hinglish naturally when the user does.
- Keep replies conversational and not unnecessarily long.
- Remember details from the current conversation.
- Be supportive without pretending to be a real human.
- Never claim to have a physical body or real-world experiences.
- Do not pressure the user into emotional dependence.
- Respect boundaries and consent.
"""

user_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "friend"

    user_histories[user_id] = []

    await update.message.reply_text(
        f"Hey {user_name} ❤️\n"
        "Main yahin hoon. Batao, aaj kya baat karni hai? 😊"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []

    await update.message.reply_text(
        "Okayy ❤️ Conversation memory reset kar di."
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
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

    # Keep recent conversation manageable
    history = history[-20:]
    user_histories[user_id] = history

    try:
        response = await asyncio.to_thread(
            client.responses.create,
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=history,
        )

        reply = response.output_text.strip()

        if not reply:
            reply = "Hmm ❤️ thoda dobara bolo, main sun rahi hoon."

        history.append({
            "role": "assistant",
            "content": reply
        })

        user_histories[user_id] = history[-20:]

        await update.message.reply_text(reply)

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text(
            "Oops 😅 abhi thodi technical problem aa gayi. "
            "Thodi der baad try karo."
        )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
