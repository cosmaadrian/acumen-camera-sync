from pytapo import Tapo
from vidgear.gears import CamGear, WriteGear
import config
import os
import cv2
import time
from collections import deque
import time
import numpy as np
from multiprocessing import Process, Array
import multiprocessing


class FrameGrabber(Process):
    def __init__(self, camera, save_event, frame_buffer, message_queue):
        super(FrameGrabber, self).__init__()
        self.camera = camera

        self.recording_path = os.path.join(config.RECORD_PATH, self.camera.name)

        self.should_stop = False

        self.frame_buffer = frame_buffer
        self.message_queue = message_queue

        self.video_out = None
        self.stream_quality = config.RECORD_QUALITY

        self.save_event = save_event

        self.do_save = False

    def stop(self):
        self.should_stop = True

    def run(self):
        viz_gear = CamGear(source = self.stream_url(kind = 'viz')).start()
        save_gear = CamGear(source = self.stream_url(kind = 'save')).start()

        while True:

            if not self.message_queue.empty():
                message = self.message_queue.get(block = False)
                if message[0] == 'start_record':
                    self.start_record(options = message[1])
                elif message[0] == 'stop_record':
                    self.stop_record()

            if self.do_save:
                self.save_event.wait()

            frame = viz_gear.read()
            hq_frame = save_gear.read()

            if frame is None:
                print("Frame is None")
                continue

            self.frame_buffer[:] = frame.ravel()

            if self.do_save:
                self.video_out.write(hq_frame)

            if self.should_stop:
                break

        if self.video_out is not None:
            self.video_out.release()

        gear.close()
        print("Finished consuming. Exiting...")

    def start_record(self, options = None):
        print(self.camera.name, "STARTING RECORDING")
        if options is not None:
            self.recording_path = os.path.join(config.RECORD_PATH, options['subject_id'], self.camera.name)
        else:
            self.recording_path = os.path.join(config.RECORD_PATH)

        os.makedirs(self.recording_path, exist_ok = True)

        if options['variation'] == '':
            variation = 'nm'
        else:
            variation = options['variation'].lower().strip()

        output_path = os.path.join(self.recording_path, variation + '-' + str(time.time())[-6:] + '.mp4')

        self.video_out = WriteGear(output_filename = output_path, logging=False)
        self.do_save = True

    @property
    def width(self):
        return config.LQ_WIDTH

    @property
    def height(self):
        return config.LQ_HEIGHT

    def stop_record(self):
        print(self.camera.name, "STOPPING RECORDING")
        self.do_save = False
        self.video_out.close()
        self.video_out = None

    def stream_url(self, kind):
        stream_type = 'stream1' if kind == 'save' else "stream2"
        return f"rtsp://{self.camera.user}:{self.camera.password}@{self.camera.host}:554/{stream_type}"

class Camera(Tapo):
    def __init__(self, name, host, user, password, save_event):
        super().__init__(host, user, password)
        self.host = host
        self.name = name
        self.user = user
        self.password = password

        self.video_out = None

        self.frame_buffer = Array('B', config.LQ_HEIGHT * config.LQ_WIDTH * 3)

        self.message_queue = multiprocessing.Queue()
        self.grabber = FrameGrabber(camera = self, save_event = save_event, frame_buffer = self.frame_buffer, message_queue = self.message_queue)

    def start_record(self, options):
        self.message_queue.put(('start_record', options))

    def stop_record(self):
        self.message_queue.put(('stop_record', None))

    def start(self):
        self.grabber.start()

    def stop(self):
        self.grabber.stop()

    def grab(self):
        frame = np.frombuffer(self.frame_buffer.get_obj(), dtype = np.uint8).reshape((config.LQ_HEIGHT, config.LQ_WIDTH, 3))
        return frame

    @property
    def width(self):
        return self.grabber.width

    @property
    def height(self):
        return self.grabber.height

    def __repr__(self):
        return f'Camera(host = {self.host}, user = {self.user})'