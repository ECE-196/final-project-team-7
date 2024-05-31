import os
from json.tool import main
from tkinter.tix import MAIN
#from typing import Final
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
from queue import Empty
# import RPi.GPIO as GPIO

TOKEN = '6635383068:AAFJituA5_o8o7L_ypkBuc0YgQlggetRee8'
BOT_USERNAME = '@facial_recognizer_bot'

flag = multiprocessing.Value('b', False)
camera_process = None
message_queue = multiprocessing.Queue()

'''
#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)
 
#set GPIO Pins
GPIO_TRIGGER = 18
GPIO_ECHO = 24
 
#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
 
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance
'''

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

    await update.message.reply_text(f'Got it! Please send me a video of {name}.')
    return VIDEO

def load_encodings(encodings_path):
    if os.path.exists(encodings_path):
        with open(encodings_path, "rb") as f:
            data = pickle.load(f)
            return data["encodings"], data["names"]
    return [], []

def save_encodings(encodings_path, encodings, names):
    with open(encodings_path, "wb") as f:
        data = {"encodings": encodings, "names": names}
        pickle.dump(data, f)

def camera_loop(flag, queue):
    # Initialize 'currentname' to trigger only when a new person is identified.
    currentname = "unknown"
    # Determine faces from encodings.pickle file model created from train_model.py
    encodingsP = "encodings.pickle"
    last_message = None

    # load the known faces and embeddings along with OpenCV's Haar
    # cascade for face detection
    print("[INFO] loading encodings + face detector...")
    knownEncodings, knownNames = load_encodings(encodingsP)
    # data = pickle.loads(open(encodingsP, "rb").read())

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
        message = None

        # loop over the facial embeddings
        for encoding in encodings:
            # attempt to match each face in the input image to our known
            # encodings
            # matches = face_recognition.compare_faces(data["encodings"], encoding)
            matches = face_recognition.compare_faces(knownEncodings, encoding)
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
                    # name = data["names"][i]
                    name = knownNames[i]
                    counts[name] = counts.get(name, 0) + 1

                # determine the recognized face with the largest number
                # of votes (note: in the event of an unlikely tie Python
                # will select first entry in the dictionary)
                name = max(counts, key=counts.get)
                #dist = distance()
                # If someone in your dataset is identified, print their name on the screen
                if currentname != name:
                    '''and dist < 12'''
                    currentname = name
                    # print(currentname)
                    message = f"It's {name} at the door."
            else: 
                message = "There's an unregistered face at the door."

            # update the list of names
            names.append(name)
        
        if message and message != last_message:
            queue.put(message)
            last_message = message

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
    global camera_process, flag, message_queue
    flag.value = False
    camera_process = multiprocessing.Process(target=camera_loop, args=(flag, message_queue))
    camera_process.start()
    await update.message.reply_text(f'Camera on. Send `/stop_cam` to stop.')

    # Start a background task to check for messages in the queue
    context.job_queue.run_repeating(check_queue, interval=1, first=0, data=update)

async def stop_cam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global camera_process, flag
    flag.value = True
    camera_process.join()
    await update.message.reply_text('Stopping camera...')

async def check_queue(context: ContextTypes.DEFAULT_TYPE):
    global message_queue
    update = context.job.data
    try:
        while True:
            message = message_queue.get_nowait()
            await update.message.reply_text(message)
    except Empty:
        pass

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        video_file = await update.message.video.get_file()
        name = context.user_data['name']
        user_id = update.message.from_user.id
        video_path = f"{user_id}_{name}.mp4"
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
        # knownEncodings = []
        # knownNames = []

        # Load existing encodings
        encodings_path = "encodings.pickle"
        knownEncodings, knownNames = load_encodings(encodings_path)

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
        '''
        data = {"encodings": knownEncodings, "names": knownNames}
        f = open(f"encodings.pickle.{name}", "wb")
        f.write(pickle.dumps(data))
        f.close()
        '''
        save_encodings(encodings_path, knownEncodings, knownNames)

        ### END OF MODEL TRAINING ###    

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
    name = update.message.text
    user_id = update.message.from_user.id

    try:
        # Load existing encodings and names
        encodings_path = 'encodings.pickle'
        knownEncodings, knownNames = load_encodings(encodings_path)

        # Find indices of the entries to be removed
        indices_to_remove = [i for i, known_name in enumerate(knownNames) if known_name == name]

        # Remove the entries
        knownEncodings = [encoding for i, encoding in enumerate(knownEncodings) if i not in indices_to_remove]
        knownNames = [known_name for i, known_name in enumerate(knownNames) if i not in indices_to_remove]

        # Save the updated encodings and names back to the file
        save_encodings(encodings_path, knownEncodings, knownNames)

        # Remove the directory containing the images
        dataset_dir = os.path.join('dataset', name)
        if os.path.exists(dataset_dir):
            import shutil
            shutil.rmtree(dataset_dir)

        await update.message.reply_text(f"Face of '{name}' removed successfully!")
    except Exception as e:
        await update.message.reply_text(f"Error removing face: {e}")
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
    encodings_path = 'encodings.pickle'
    knownEncodings, knownNames = load_encodings(encodings_path)
    if knownNames:  # Check if any faces are registered
        face_list = "\n".join(f"- {name}" for name in set(knownNames))
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
    
