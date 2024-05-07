from json.tool import main
from tkinter.tix import MAIN
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes 


TOKEN: Final = '6635383068:AAFJituA5_o8o7L_ypkBuc0YgQlggetRee8'
BOT_USERNAME: Final = '@facial_recognizer_bot'

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! We are here to help you to identify visitors at your doorstep.')

# /add_face command
NAME, PHOTO = range(2)

async def add_face(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Please send me the name of the person.')
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['name'] = name
    await update.message.reply_text(f'Got it! Please send me a photo of {name}.')
    return PHOTO

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"{context.user_data['name']}.jpg"
    await photo_file.download_to_drive(photo_path) # saved to current directory, change later to save it in database
    await update.message.reply_text('Photo has been saved successfully.')
    return ConversationHandler.END

#  Starting the bot
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    add_face_handler = ConversationHandler(
        entry_points=[CommandHandler('add_face', add_face)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(add_face_handler)
    
    app.run_polling()