import os
from json.tool import main
from tkinter.tix import MAIN
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes 


TOKEN: Final = '6635383068:AAFJituA5_o8o7L_ypkBuc0YgQlggetRee8'
BOT_USERNAME: Final = '@facial_recognizer_bot'

recognized_faces = {} 
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
    try:
        photo_file = await update.message.photo[-1].get_file()
        name = context.user_data['name']
        photo_path = f"{name}.jpg"
        await photo_file.download_to_drive(photo_path)

        # Add to the dictionary:
        recognized_faces[name] = photo_path  

        await update.message.reply_text(f"Face of '{name}' added successfully!")
    except Exception as e:
        await update.message.reply_text(f"Error adding face: {e}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

REMOVE_NAME = range(1)  # State for getting the name

async def remove_face(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Please send me the name of the person to remove.')
    return REMOVE_NAME

async def remove_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name_to_remove = update.message.text
    if name_to_remove in recognized_faces:
        photo_path = f"{name_to_remove}.jpg"
        if os.path.exists(photo_path):  # Check if the file exists
            os.remove(photo_path)        # Delete the photo
            del recognized_faces[name_to_remove]
            await update.message.reply_text(f"Removed {name_to_remove} and their photo successfully.")
        else:
            await update.message.reply_text(f"Photo for {name_to_remove} was not found.")
    else:
        await update.message.reply_text(f"{name_to_remove} is not a recognized face.")
    return ConversationHandler.END
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Here are the available commands:
    /add_face - Register a new face.
    /identify_face - Identify a person in a photo.
    /list_faces - View all registered faces.
    /help - Show this help message.
    """
    await update.message.reply_text(help_text)

async def list_faces(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if recognized_faces:  # Check if any faces are registered
        face_list = "\n".join(f"- {name}" for name in recognized_faces)
        await update.message.reply_text(f"Recognized faces:\n{face_list}")
    else:
        await update.message.reply_text("No faces registered yet.")

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

    remove_face_handler = ConversationHandler(
        entry_points=[CommandHandler('remove_face', remove_face)],
        states={
            REMOVE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_name)]
        },
        fallbacks=[]
    )

    app.add_handler(add_face_handler)
    app.add_handler(remove_face_handler)

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command)) 

    
    app.run_polling()