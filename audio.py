import zmq
import pyaudio
from queue import Queue, Full, Empty
import struct
from threading import Thread


class AudioManager:
    socket: zmq.Socket
    read_stream: pyaudio.Stream
    read_queue: Queue
    write_stream: pyaudio.Stream
    write_queue: Queue

    def __init__(self):
        self.read_queue = Queue(maxsize=8 * 1024)
        self.write_queue = Queue(maxsize=8 * 1024)

        def read_callback(in_data, frame_count, time_info, status):
            for (frame,) in struct.iter_unpack("=f", in_data):
                try:
                    self.read_queue.put_nowait(frame)
                    self.read_queue.task_done()
                except Full:
                    pass

            return (None, pyaudio.paContinue)

        def write_callback(in_data, frame_count, time_info, status):
            out_data = b""
            for _ in range(frame_count):
                try:
                    frame = self.read_queue.get_nowait()
                except Empty:
                    frame = 0

                out_data += struct.pack("=f", frame)

            return (out_data, pyaudio.paContinue)

        p = pyaudio.PyAudio()

        self.read_stream = p.open(
            rate=44100,
            channels=1,
            format=pyaudio.paFloat32,
            stream_callback=read_callback,
            input=True,
        )

        self.write_stream = p.open(
            rate=44100,
            channels=1,
            format=pyaudio.paFloat32,
            stream_callback=write_callback,
            output=True,
        )

        while self.read_stream.is_active() or self.write_stream.is_active():
            pass


AudioManager()
