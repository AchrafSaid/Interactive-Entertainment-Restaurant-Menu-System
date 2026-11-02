import cv2
import mediapipe as mp
import dollarpy
import numpy as np
import tkinter as tk

if not hasattr(mp, "solutions"):
    raise RuntimeError(
        "This project needs MediaPipe 0.10.21 with mp.solutions. "
        "Install requirements.txt and run .venv/bin/python test_libraries.py."
    )

# Check the actual APIs used by the gesture controller, not only the import.
mp.solutions.hands.Hands
mp.solutions.drawing_utils.draw_landmarks

print("OpenCV:", cv2.__version__)
print("MediaPipe:", mp.__version__)
print("DollarPy: Imported successfully!")
print("NumPy:", np.__version__)
print("Tkinter:", tk.TkVersion)

print("\nAll libraries are working!")
