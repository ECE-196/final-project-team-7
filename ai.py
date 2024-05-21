import os
import pandas as pd
import cv2
import tensorflow.python.keras as keras
import numpy as np
from keras.layers import Dense, Dropout, Flatten, Input
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import BatchNormalization
from keras.optimizers import Adam
from keras.models import Sequential
from keras.utils import to_categorical
from skimage import io
##TODO: add the training directory
data_dir = ''


cv2.imread('image.jpg')