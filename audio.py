import struct
import zlib
from collections import deque
from queue import Empty, Queue
from threading import Event, Thread

import pyaudio
import zmq

SAMPLE_RATE = 16000


class AudioStream:
    _stream: pyaudio.Stream
    _thread: Thread
    _buffer: Queue
    _shutdown: Event

    def __init__(self, p: pyaudio.PyAudio = None):
        if not p:
            p = pyaudio.PyAudio()

        self._buffer = Queue()
        self._shutdown = Event()

        self._stream = p.open(
            rate=SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            output=True,
        )

        self._thread = Thread(target=self._write_audio_data)
        self._thread.start()

    def write(self, data: bytes):
        self._buffer.put(data)

    def stop(self):
        self._shutdown.set()
        self._stream.close()

    def _write_audio_data(self):
        while not self._shutdown.is_set():
            try:
                data = self._buffer.get(timeout=0.5)
            except Empty:
                continue
            data = zlib.decompress(data)

            native_data = b""
            for (frame,) in struct.iter_unpack("!h", data):
                native_data += struct.pack("=h", frame)

            try:
                self._stream.write(native_data)
            except OSError:
                # Stream closed
                return


class AudioManager:
    _p: pyaudio.PyAudio
    _socket: zmq.Socket
    _read_stream: pyaudio.Stream
    _read_queue: Queue
    _reading_thread: Thread
    _write_streams: dict[str, AudioStream]
    _shutdown: Event

    _last_frame: int

    def __init__(self, poller: zmq.Poller):
        self._p = pyaudio.PyAudio()
        context = zmq.Context.instance()

        self._read_queue = Queue()
        self._shutdown = Event()

        self._socket: zmq.Socket = context.socket(zmq.PULL)
        self._socket.bind(f"inproc://audio")

        poller.register(self._socket)

        def read_callback(in_data, frame_count, time_info, status):
            for (frame,) in struct.iter_unpack("=h", in_data):
                self._read_queue.put(frame)

            return (None, pyaudio.paContinue)

        self._read_stream = self._p.open(
            rate=SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            stream_callback=read_callback,
            input=True,
        )

        self._reading_thread = Thread(target=self._read_audio_data)
        self._reading_thread.start()

        self._write_streams = {}

    def is_in(self, events: dict) -> bool:
        return self._socket in events

    def read(self) -> bytes:
        try:
            data = self._socket.recv(zmq.DONTWAIT)
        except zmq.ZMQError:
            data = b""

        return data

    def write(self, data: bytes, username: str):
        stream = self._write_streams.get(username)
        if not stream:
            stream = AudioStream(self._p)
            self._write_streams[username] = stream

        stream.write(data)

    def stop(self):
        self._shutdown.set()
        self._read_stream.close()
        for stream in self._write_streams.values():
            stream.stop()

    def _read_audio_data(self):
        context = zmq.Context.instance()

        socket: zmq.Socket = context.socket(zmq.PUSH)
        socket.connect(f"inproc://audio")

        data = b""
        while not self._shutdown.is_set():
            try:
                frame = self._read_queue.get(timeout=0.5)
            except Empty:
                continue

            data += struct.pack("!h", frame)

            if len(data) >= 2048:
                data = zlib.compress(data)

                socket.send(data)
                data = b""
