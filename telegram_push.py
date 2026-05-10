from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

async def send_channel_message(text):
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        return True
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False