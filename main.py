import os
import json
from json.tool import main
from tkinter.tix import MAIN
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes 


TOKEN: Final = '6635383068:AAFJituA5_o8o7L_ypkBuc0YgQlggetRee8'
BOT_USERNAME: Final = '@facial_recognizer_bot'

# recognized_faces = {} 

# Function to generate the file path for a user's data based on their user ID
def get_user_data_file(user_id):
    return f"user_data_{user_id}.json"

def save_user_data(user_id, data):
    file_path = get_user_data_file(user_id)
    with open(file_path, 'w') as f:
        json.dump(data, f)

def load_user_data(user_id):
    file_path = get_user_data_file(user_id)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {} # Return an empty dictionary if the file doesn't exist

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! We are here to help you to identify visitors at your doorstep.')

NAME, VIDEO, REMOVE_NAME = range(3)

# /add_face command
async def add_face(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Please send me the name of the person.')
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    user_id = update.message.from_user.id
    context.user_data['name'] = name

    # Load user data
    user_data = load_user_data(user_id)
    context.user_data['recognized_faces'] = user_data

    await update.message.reply_text(f'Got it! Please send me a video of {name}.')
    return VIDEO

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        video_file = await update.message.video.get_file()
        name = context.user_data['name']
        user_id = update.message.from_user.id
        video_path = f"{user_id}_{name}_{video_file.file_unique_id}.mp4"
        await video_file.download_to_drive(video_path)

        # Add to the dictionary:
        # recognized_faces[name] = video_path  

        # Load user data
        user_data = context.user_data.get('recognized_faces', {})
        if name in user_data:
            user_data[name].append(video_path)  # Add the new video path to the list
        else:
            user_data[name] = [video_path]  # Create a new list with the video path

        # Save user data
        save_user_data(user_id, user_data)

        await update.message.reply_text(f"Face of '{name}' added successfully!")
    except Exception as e:
        await update.message.reply_text(f"Error adding face: {e}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

async def remove_face(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Please send me the name of the person to remove.')
    return REMOVE_NAME

async def remove_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name_to_remove = update.message.text
    user_id = update.message.from_user.id
    user_data = load_user_data(user_id)

    if name_to_remove in user_data:
        video_paths = user_data[name_to_remove]
        for video_path in video_paths:
            if os.path.exists(video_path):  # Check if the file exists
                os.remove(video_path)        # Delete the video
        del user_data[name_to_remove]    # Remove the name from the dictionary
        save_user_data(user_id, user_data)  # Save updated data
        await update.message.reply_text(f"Removed {name_to_remove} and all associated videos successfully.")
    else:
        await update.message.reply_text(f"{name_to_remove} is not a recognized face.")
    return ConversationHandler.END
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Here are the available commands:
    /add_face - Register a new face.
    /remove_face - Remove a registered face.
    /list_faces - View all registered faces.
    /help - Show this help message.
    """
    await update.message.reply_text(help_text)

async def list_faces(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = load_user_data(user_id)
    if user_data:  # Check if any faces are registered
        face_list = "\n".join(f"- {name} ({len(videos)} videos)" for name, videos in user_data.items())
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
            VIDEO: [MessageHandler(filters.VIDEO, video)],
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
    app.add_handler(CommandHandler('list_faces', list_faces))

    
    app.run_polling()
    
