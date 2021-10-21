from pytapo import Tapo
from vidgear.gears import CamGear, WriteGear
import config
import os
import cv2
import time
from collections import deque
import sys
import time
import numpy as np
from multiprocessing import Process, Array
import multiprocessing
import threading
import queue

class BufferLessCamGear(object):
    def __init__(self, source):
        self.cap = CamGear(source = source, CAP_PROP_BUFFERSIZE=1).start()
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def _reader(self):
        while True:
            frame = self.cap.read()
            if frame is None:
                continue

            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return self.q.get()

    def stop(self):
        self.cap.stop()


class FrameGrabber(Process):
    def __init__(self, camera, save_event, stop_event, frame_buffer, message_queue, output_queue):
        super(FrameGrabber, self).__init__()
        self.camera = camera

        self.recording_path = os.path.join(config.RECORD_PATH, self.camera.name)

        self.should_stop = False

        self.frame_buffer = frame_buffer
        self.message_queue = message_queue
        self.output_queue = output_queue

        self._last_video = ''

        self.video_out = None
        self.symbol = self.camera.symbol
        self.stream_quality = config.RECORD_QUALITY

        self.save_event = save_event
        self.stop_event = stop_event
        self.fps = 16
        self.written_frames = 0
        self.start_time = None

        self.do_save = False

    def stop(self):
        self.should_stop = True

    def run(self):
        viz_gear = BufferLessCamGear(self.stream_url(kind = 'viz'))

        while True:

            if not self.message_queue.empty():
                message = self.message_queue.get(block = False)
                if message[0] == 'start_record':
                    self.start_record(options = message[1])
                elif message[0] == 'stop_record':
                    self.stop_record()

            if self.do_save:
                self.save_event.wait()
                hq_frame = self.save_gear.read()

            start_time = time.time()
            frame = viz_gear.read()
            end_time = time.time()

            if frame is None:
                print("Frame is None")
                continue

            start_time = time.time()
            if not self.do_save:
                self.frame_buffer[:] = frame.ravel()
            end_time = time.time()

            if self.do_save:
                print(self.symbol, end='')
                sys.stdout.flush()
                self.video_out.write(hq_frame)
                self.written_frames += 1

            if self.should_stop:
                break

        if self.video_out is not None:
            self.video_out.release()

        viz_gear.stop()
        save_gear.stop()
        print("Finished consuming. Exiting...")

    def start_record(self, options = None):
        print(self.camera.name, "STARTING RECORDING")
        if options is not None:
            subject_id = options['subject_id'].strip().replace(' ', '-').lower()
            self.recording_path = os.path.join(config.RECORD_PATH, subject_id, self.camera.name)
        else:
            self.recording_path = os.path.join(config.RECORD_PATH)

        os.makedirs(self.recording_path, exist_ok = True)

        if options['variation'] == '':
            variation = 'nm'
        else:
            variation = options['variation'].lower().strip()

        output_path = os.path.join(self.recording_path, self.camera.name + '-' + variation + '-' + str(time.time()).replace('.', '-') + '.avi')
        self.output_queue.put(('last_video', output_path))
        self.save_gear = CamGear(self.stream_url(kind = 'save')).start()

        ##############################
        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        self.video_out = cv2.VideoWriter(output_path, fourcc, self.fps, (config.HQ_WIDTH, config.HQ_HEIGHT))
        ##############################

        self.do_save = True
        self.start_time = time.time()

    def stop_record(self):
        stop_time = time.time()
        expected_num_frames = int((stop_time - self.start_time) + 1) * self.fps
        actual_num_frames = self.written_frames
        difference = expected_num_frames - actual_num_frames

        if difference > 0:
            print(f"[{self.camera.name}] Saving remaining {difference} frames.")
            while difference > 0:
                hq_frame = self.save_gear.read()
                self.video_out.write(hq_frame)
                difference -= 1
                self.written_frames += 1

        print(self.camera.name, "STOPPING RECORDING")
        self.stop_event.wait()
        self.do_save = False
        self.save_gear.stop()
        self.save_gear = None

        print(self.camera.name, f'Written {self.written_frames} / {expected_num_frames}')

        # self.video_out.close()
        self.video_out.release()
        self.video_out = None
        self.written_frames = 0

    @property
    def width(self):
        return config.LQ_WIDTH

    @property
    def height(self):
        return config.LQ_HEIGHT

    def stream_url(self, kind):
        stream_type = 'stream1' if kind == 'save' else "stream2"
        return f"rtsp://{self.camera.user}:{self.camera.password}@{self.camera.host}:554/{stream_type}"

class Camera(Tapo):
    def __init__(self, name, host, user, password, symbol, save_event, stop_event):
        super().__init__(host, user, password)
        self.host = host
        self.name = name
        self.user = user
        self.symbol = symbol
        self.password = password

        self.video_out = None

        self.frame_buffer = Array('B', config.LQ_HEIGHT * config.LQ_WIDTH * 3)

        self.message_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.grabber = FrameGrabber(
            camera = self,
            save_event = save_event,
            stop_event = stop_event,
            frame_buffer = self.frame_buffer,
            message_queue = self.message_queue,
            output_queue = self.output_queue
        )

    def start_record(self, options):
        self.message_queue.put(('start_record', options))

    def stop_record(self):
        self.message_queue.put(('stop_record', None))

    def start(self):
        self.grabber.start()

    def stop(self):
        self.grabber.stop()

    @property
    def last_video(self):
        key, path = self.output_queue.get('last_video')
        return path

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
