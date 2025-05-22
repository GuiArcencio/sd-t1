import zlib
from queue import Empty, Queue
from threading import Event, Thread

import cv2
import numpy as np
import zmq


class VideoStream:
    _username: str
    _thread: Thread
    _buffer: Queue
    _shutdown: Event

    def __init__(self, username: str):
        self._username = username
        self._buffer = Queue()
        self._shutdown = Event()

        self._thread = Thread(target=self._write_video_data)
        self._thread.start()

    def write(self, data: bytes):
        self._buffer.put(data)

    def stop(self):
        self._shutdown.set()
        cv2.destroyWindow(self._username)

    def _write_video_data(self):
        while not self._shutdown.is_set():
            try:
                data = self._buffer.get(timeout=0.5)
            except Empty:
                continue
            frame = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(frame, 1)

            cv2.imshow(self._username, frame)

            cv2.waitKey(20)


class VideoManager:
    _socket: zmq.Socket
    _camera: cv2.VideoCapture
    _streams: dict[str, VideoStream]
    _reading_thread: Thread
    _shutdown: Event

    def __init__(self, poller: zmq.Poller):
        context = zmq.Context.instance()

        self._socket: zmq.Socket = context.socket(zmq.PULL)
        self._socket.bind(f"inproc://video")

        poller.register(self._socket)

        self._shutdown = Event()

        self._streams = {}

        self._camera = cv2.VideoCapture(0)

        self._reading_thread = Thread(target=self._read_video_data)
        self._reading_thread.start()

    def is_in(self, events: dict) -> bool:
        return self._socket in events

    def stop(self):
        self._shutdown.set()
        self._camera.release()
        for stream in self._streams.values():
            stream.stop()

    def read(self) -> bytes:
        try:
            data = self._socket.recv(zmq.DONTWAIT)
        except zmq.ZMQError:
            data = b""

        return data

    def write(self, data: bytes, username: str):
        stream = self._streams.get(username)
        if not stream:
            stream = VideoStream(username)
            self._streams[username] = stream

        stream.write(data)

    def _read_video_data(self):
        context = zmq.Context.instance()

        socket: zmq.Socket = context.socket(zmq.PUSH)
        socket.connect(f"inproc://video")

        while not self._shutdown.is_set():
            ret, frame = self._camera.read()
            if ret:
                frame = cv2.resize(
                    frame, dsize=(320, 240), interpolation=cv2.INTER_AREA
                )
                _, frame = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                socket.send(frame.tobytes(order="C"))
