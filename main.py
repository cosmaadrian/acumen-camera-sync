from PIL import ImageTk, Image
from camera import Camera
import config
import tkinter
import cv2
import numpy as np
import time
import multiprocessing

class App():
    def __init__(self, window, window_title, cameras):
        self.window = window
        self.window.title(window_title)
        self.delay = 50
        self.is_recording = False

        self.manager = multiprocessing.Manager()
        self.save_event = self.manager.Event()
        self.save_event.clear()

        self.cameras = [Camera(save_event = self.save_event, **config) for config in cameras]

        self.app = tkinter.Frame(window, bg="white")
        self.app.pack()

        self.canvas = tkinter.Canvas(self.app, width = config.LQ_WIDTH * len(cameras) * 0.8, height = config.LQ_HEIGHT)
        self.canvas.pack()

        self.init_controls()
        self.init_cameras()

        self.update()
        self.window.mainloop()

    def init_controls(self):
        self.btn_text = tkinter.StringVar()
        self.btn_text.set('START RECORD')

        self.btn_record = tkinter.Button(self.window, textvariable=self.btn_text, height = 5, width=10, font = ("Helvetica", 15), command=self.record, bg='#eb1313', fg = 'White')
        self.btn_record.pack()

        label = tkinter.Label(self.window, text = 'Experiment Setup')

        self.is_abnormal = tkinter.IntVar()
        c = tkinter.Checkbutton(self.window, text = "Python", variable = self.is_abnormal)
        c.pack()

    def init_cameras(self):
        for c in self.cameras:
            c.start()

    def record(self):
        print(self.is_abnormal.get())
        if self.is_recording:
            self.btn_text.set('START RECORD')

            for camera in self.cameras:
                camera.stop_record()

            self.save_event.clear()

        else:
            self.btn_text.set('STOP RECORD')
            for camera in self.cameras:
                camera.start_record(options = {'lol': 'lol'})

            self.save_event.set()

        self.is_recording = not self.is_recording

    def update(self):
        images = []
        start_time = time.time()
        for camera in self.cameras:
            frame = camera.grab()
            if frame is None:
                frame = np.zeros((camera.height, camera.width, 3), dtype = np.uint8)
            images.append(frame)
        end_time = time.time()

        images = cv2.hconcat(images)
        images = cv2.cvtColor(images, cv2.COLOR_BGR2RGB)
        images = cv2.resize(images, dsize = None, fx = 0.8, fy = 0.8)

        self.photo = ImageTk.PhotoImage(image = Image.fromarray(images))
        self.canvas.create_image(0, 0, image = self.photo, anchor = tkinter.NW)

        self.window.after(self.delay, self.update)

app = App(
    tkinter.Tk(),
    'AcumenEyes',
    cameras = config.CAMERAS
)