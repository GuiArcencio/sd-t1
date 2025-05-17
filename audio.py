import zmq
import pyaudio
from queue import Queue, Empty
import struct
from threading import Thread, Event
from collections import deque
import zlib


class AudioManager:
    _socket: zmq.Socket
    _read_stream: pyaudio.Stream
    _read_queue: Queue
    _write_stream: pyaudio.Stream
    _write_queue: Queue
    _buffer_queue: Queue
    _reading_thread: Thread
    _writing_thread: Thread
    _shutdown: Event

    def __init__(self, poller: zmq.Poller):
        p = pyaudio.PyAudio()
        context = zmq.Context.instance()

        self._read_queue = Queue()
        self._write_queue = Queue()
        self._buffer_queue = Queue()

        self._socket: zmq.Socket = context.socket(zmq.PULL)
        self._socket.bind(f"inproc://audio")

        poller.register(self._socket)

        def read_callback(in_data, frame_count, time_info, status):
            for (frame,) in struct.iter_unpack("=h", in_data):
                self._read_queue.put(frame)

            return (None, pyaudio.paContinue)

        def write_callback(in_data, frame_count, time_info, status):
            out_data = b""
            for _ in range(frame_count):
                try:
                    frame = self._write_queue.get_nowait()
                except Empty:
                    frame = 0

                out_data += struct.pack("=h", frame)

            return (out_data, pyaudio.paContinue)

        self._read_stream = p.open(
            rate=44100,
            channels=1,
            format=pyaudio.paInt16,
            stream_callback=read_callback,
            input=True,
        )

        self._write_stream = p.open(
            rate=44100,
            channels=1,
            format=pyaudio.paInt16,
            output=True,
        )

        self._shutdown = Event()
        self._reading_thread = Thread(target=self._read_audio_data)
        self._reading_thread.start()
        self._writing_thread = Thread(target=self._write_audio_data)
        self._writing_thread.start()

    def is_in(self, events: dict) -> bool:
        return self._socket in events

    def read(self) -> bytes:
        try:
            data = self._socket.recv(zmq.DONTWAIT)
        except zmq.ZMQError:
            data = b""

        return data

    def write(self, data: bytes):
        self._buffer_queue.put(zlib.decompress(data))

    def stop(self):
        self._shutdown.set()
        self._read_stream.close()
        self._write_stream.close()

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

    def _write_audio_data(self):
        buffer = b""

        while not self._shutdown.is_set():
            try:
                data = self._buffer_queue.get(timeout=0.5)
            except Empty:
                continue

            for (frame,) in struct.iter_unpack("!h", data):
                buffer += struct.pack("=h", frame)
                if len(buffer) > 44100 * 2:
                    write_data = buffer[:44100]
                    buffer = buffer[44100:]

                    self._write_stream.write(write_data)
