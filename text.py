import zmq
from threading import Thread


def _text_reader_thread(socket_name: str = "text", context: zmq.Context = None):
    context = context or zmq.Context.instance()

    socket: zmq.Socket = context.socket(zmq.PAIR)
    socket.connect(f"inproc://{socket_name}")

    while True:
        message = input()
        if message:
            socket.send_string(message)


class TextReader:
    socket: zmq.Socket
    reading_thread: Thread

    def __init__(self, socket_name: str = "text", context: zmq.Context = None):
        context = context or zmq.Context.instance()

        self.socket: zmq.Socket = context.socket(zmq.PAIR)
        self.socket.bind(f"inproc://{socket_name}")

        self.reading_thread = Thread(target=_text_reader_thread, args=(socket_name,))
        self.reading_thread.start()
