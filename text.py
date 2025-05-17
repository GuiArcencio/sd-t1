import zmq
import asyncio
from threading import Thread, Event, Lock
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Log, Input
from textual.containers import VerticalGroup


class TextApp(App):
    AUTO_FOCUS = "Input"

    socket: zmq.Socket
    chat_lock: Lock
    username: str

    def __init__(
        self,
        username: str,
        driver_class=None,
        css_path=None,
        watch_css=False,
        ansi_color=False,
    ):
        super().__init__(driver_class, css_path, watch_css, ansi_color)

        context = zmq.Context.instance()

        self.chat_lock = Lock()
        self.socket: zmq.Socket = context.socket(zmq.PUSH)
        self.socket.connect(f"inproc://text")
        self.username = username

    def compose(self) -> ComposeResult:
        yield VerticalGroup(Log(), Input(placeholder="...", select_on_focus=False))

    @on(Input.Submitted)
    def handler(self, event: Input.Submitted):
        if event.value:
            self.write_message(self.username, event.value)

            self.socket.send_string(event.value)

            event.input.value = ""

    def write_message(self, username: str, message: str):
        with self.chat_lock:
            chat = self.query_one(Log)

            chat.write_line(f"{username}> {message}", scroll_end=True)


class TextManager:
    _socket: zmq.Socket
    _shutdown: Event
    _textapp: TextApp
    _appthread: Thread

    def __init__(self, username: str, poller: zmq.Poller):
        context = zmq.Context.instance()

        self._socket: zmq.Socket = context.socket(zmq.PULL)
        self._socket.bind(f"inproc://text")

        poller.register(self._socket, zmq.POLLIN)

        self._textapp = TextApp(username=username)
        self._appthread = Thread(target=self._run_app)
        self._appthread.start()

        self._shutdown = Event()

    def is_in(self, events: dict) -> bool:
        return self._socket in events

    def read(self) -> str:
        try:
            text = self._socket.recv_string(zmq.DONTWAIT)
        except zmq.ZMQError:
            text = ""

        return text

    def write(self, username: str, text: str):
        writing_thread = Thread(target=self._write, args=(username, text))
        writing_thread.start()

    def user_has_quit(self) -> bool:
        return self._shutdown.is_set()

    def _run_app(self):
        loop = asyncio.new_event_loop()
        self._textapp.run(loop=loop)

        self._shutdown.set()

    def _write(self, username: str, text: str):
        self._textapp.write_message(username, text)
