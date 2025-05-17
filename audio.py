import zmq
import pyaudio
from queue import Queue, Full, Empty
import struct
from threading import Thread, Event


class AudioManager:
    _socket: zmq.Socket
    _read_stream: pyaudio.Stream
    _read_queue: Queue
    _write_stream: pyaudio.Stream
    _write_queue: Queue
    _reading_thread: Thread
    _shutdown: Event

    def __init__(self, poller: zmq.Poller):
        p = pyaudio.PyAudio()
        context = zmq.Context.instance()

        self._read_queue = Queue(maxsize=8 * 1024)
        self._write_queue = Queue(maxsize=8 * 1024)

        self._socket: zmq.Socket = context.socket(zmq.PULL)
        self._socket.bind(f"inproc://audio")

        poller.register(self._socket)

        def read_callback(in_data, frame_count, time_info, status):
            for (frame,) in struct.iter_unpack("=f", in_data):
                try:
                    self._read_queue.put_nowait(frame)
                except Full:
                    pass

            return (None, pyaudio.paContinue)

        def write_callback(in_data, frame_count, time_info, status):
            out_data = b""
            for _ in range(frame_count):
                try:
                    frame = self._write_queue.get_nowait()
                except Empty:
                    frame = 0

                out_data += struct.pack("=f", frame)

            return (out_data, pyaudio.paContinue)

        self._read_stream = p.open(
            rate=44100,
            channels=1,
            format=pyaudio.paFloat32,
            stream_callback=read_callback,
            input=True,
        )

        self._write_stream = p.open(
            rate=44100,
            channels=1,
            format=pyaudio.paFloat32,
            stream_callback=write_callback,
            output=True,
        )

        self._shutdown = Event()
        self._reading_thread = Thread(target=self._read_audio_data)
        self._reading_thread.start()

    def is_in(self, events: dict) -> bool:
        return self._socket in events

    def read(self) -> bytes:
        try:
            data = self._socket.recv(zmq.DONTWAIT)
        except zmq.ZMQError:
            data = b""

        return data

    def write(self, data: bytes):
        writing_thread = Thread(target=self._write, args=(data,))
        writing_thread.start()

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
                data += struct.pack("!f", frame)

                if len(data) >= 256:
                    socket.send(data)
                    data = b""
            except Empty:
                pass

    def _write(self, data: bytes):
        for (frame,) in struct.iter_unpack("!f", data):
            try:
                self._write_queue.put_nowait(frame)
            except Full:
                pass
