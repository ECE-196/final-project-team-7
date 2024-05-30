import os
import json
from json.tool import main
from tkinter.tix import MAIN
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes 
import cv2
import pickle
import face_recognition
from imutils.video import VideoStream
from imutils.video import FPS
import imutils
import time
from imutils import paths
import multiprocessing


TOKEN: Final = '6635383068:AAFJituA5_o8o7L_ypkBuc0YgQlggetRee8'
BOT_USERNAME: Final = '@facial_recognizer_bot'

flag = multiprocessing.Value('b', False)
camera_process = None

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

def camera_loop(flag):
    # Initialize 'currentname' to trigger only when a new person is identified.
    currentname = "unknown"
    # Determine faces from encodings.pickle file model created from train_model.py
    encodingsP = "encodings.pickle"

    # load the known faces and embeddings along with OpenCV's Haar
    # cascade for face detection
    print("[INFO] loading encodings + face detector...")
    data = pickle.loads(open(encodingsP, "rb").read())

    # initialize the video stream and allow the camera sensor to warm up
    vs = VideoStream(src=0, framerate=10).start()
    time.sleep(2.0)

    # start the FPS counter
    fps = FPS().start()
    
    # loop over frames from the video file stream
    while not flag.value:
        # grab the frame from the threaded video stream and resize it
        frame = vs.read()
        frame = imutils.resize(frame, width=500)
        # Detect the face boxes
        boxes = face_recognition.face_locations(frame)
        # compute the facial embeddings for each face bounding box
        encodings = face_recognition.face_encodings(frame, boxes)
        names = []

        # loop over the facial embeddings
        for encoding in encodings:
            # attempt to match each face in the input image to our known
            # encodings
            matches = face_recognition.compare_faces(data["encodings"], encoding)
            name = "Unknown" # if face is not recognized, then print Unknown

            # check to see if we have found a match
            if True in matches:
                # find the indexes of all matched faces then initialize a
                # dictionary to count the total number of times each face
                # was matched
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                # loop over the matched indexes and maintain a count for
                # each recognized face
                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                # determine the recognized face with the largest number
                # of votes (note: in the event of an unlikely tie Python
                # will select first entry in the dictionary)
                name = max(counts, key=counts.get)

                # If someone in your dataset is identified, print their name on the screen
                if currentname != name:
                    currentname = name
                    print(currentname)

            # update the list of names
            names.append(name)

        # loop over the recognized faces
        for ((top, right, bottom, left), name) in zip(boxes, names):
            # draw the predicted face name on the image - color is in BGR
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 225), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)

        # display the image to our screen
        cv2.imshow("Facial Recognition is Running", frame)
        key = cv2.waitKey(1) & 0xFF

        # update the FPS counter
        fps.update()

    # stop the timer and display FPS information
    fps.stop()
    print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
    print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

    # do a bit of cleanup
    cv2.destroyAllWindows()
    vs.stop()

async def open_cam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global camera_process, flag
    flag.value = False
    await update.message.reply_text(f'Camera on. Send `/stop_cam` to stop.')
    camera_process = multiprocessing.Process(target=camera_loop, args=(flag,))
    camera_process.start()

async def stop_cam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global camera_process, flag
    flag.value = True
    camera_process.join()
    await update.message.reply_text('Stopping camera...')

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        video_file = await update.message.video.get_file()
        name = context.user_data['name']
        user_id = update.message.from_user.id
        video_path = f"{user_id}_{name}_{video_file.file_unique_id}.mp4"
        await video_file.download_to_drive(video_path)

        #make directory for images
        output_dir = os.path.join('dataset', name)
        os.makedirs(output_dir, exist_ok=True)
        
        vidcap = cv2.VideoCapture(video_path)
        success,image = vidcap.read()
        count = 0       

        # number of frames to skip
        numFrameToSave = 12
        frame_cnt = 0
        while success: # check success here might break your program
            success,image = vidcap.read() #success might be false and image might be None
            #check success here
            if not success:
                break

            # on every numFrameToSave 
            if (count % numFrameToSave ==0):  
                frame_path = os.path.join(output_dir, "%s_%d.jpg" % (name, frame_cnt))
                cv2.imwrite(frame_path, image)
                frame_cnt += 1  

            if cv2.waitKey(10) == 27:                     
                break
            count += 1
        # Add to the dictionary:
        # recognized_faces[name] = video_path  


        ## MODEL TRAINING ## 
        
        imagePaths = list(paths.list_images(f"dataset/{name}"))        
        # initialize the list of known encodings and known names
        knownEncodings = []
        knownNames = []

        # loop over the image paths
        for (i, imagePath) in enumerate(imagePaths):
        # extract the person name from the image path
            print("[INFO] processing image {}/{}".format(i + 1,
            len(imagePaths)))
        name = imagePath.split(os.path.sep)[-2]

        # load the input image and convert it from RGB (OpenCV ordering)
        # to dlib ordering (RGB)
        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # detect the (x, y)-coordinates of the bounding boxes
        # corresponding to each face in the input image
        boxes = face_recognition.face_locations(rgb,
            model="hog")

        # compute the facial embedding for the face
        encodings = face_recognition.face_encodings(rgb, boxes)

        # loop over the encodings
        for encoding in encodings:
            # add each encoding + name to our set of known names and
            # encodings
            knownEncodings.append(encoding)
            knownNames.append(name)

        # dump the facial encodings + names to disk
        print("[INFO] serializing encodings...")
        data = {"encodings": knownEncodings, "names": knownNames}
        f = open("encodings.pickle", "wb")
        f.write(pickle.dumps(data))
        f.close()

        ### END OF MODEL TRAINING ###
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
    /open_cam - open the camera.
    /stop_cam - stop the camera.
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
    app.add_handler(CommandHandler('open_cam', open_cam))
    app.add_handler(CommandHandler('stop_cam', stop_cam))


    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command)) 
    app.add_handler(CommandHandler('list_faces', list_faces))

    app.run_polling()
    
