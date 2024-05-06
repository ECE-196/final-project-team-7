from json.tool import main
from tkinter.tix import MAIN
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes 


TOKEN: Final = '6635383068:AAFJituA5_o8o7L_ypkBuc0YgQlggetRee8'
BOT_USERNAME: Final = '@facial_recognizer_bot'

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello!')

# def handle_response(text: str) -> str:
#     processed: str = text.lower()

if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    
    app.run_polling()