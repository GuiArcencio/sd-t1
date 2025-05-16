import zmq
from threading import Thread


class TextManager:
    _socket: zmq.Socket
    _reading_thread: Thread

    def __init__(self, poller: zmq.Poller):
        context = zmq.Context.instance()

        self._socket: zmq.Socket = context.socket(zmq.PULL)
        self._socket.bind(f"inproc://text")

        poller.register(self._socket, zmq.POLLIN)

        self._reading_thread = Thread(target=self._read_loop)
        self._reading_thread.start()

    def is_in(self, events: dict) -> bool:
        return self._socket in events

    def read(self) -> str:
        try:
            text = self._socket.recv_string(zmq.DONTWAIT)
        except zmq.ZMQError:
            text = ""

        return text

    def _read_loop(self):
        context = zmq.Context.instance()

        socket: zmq.Socket = context.socket(zmq.PAIR)
        socket.connect(f"inproc://text")

        while True:
            message = input()
            if message:
                socket.send_string(message)

    def write(self, text: str):
        writing_thread = Thread(target=self._write, args=(text,))
        writing_thread.start()

    def _write(self, text: str):
        print(text)
