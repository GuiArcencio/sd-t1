import zmq


from message import MessageFrame


class NetworkManager:
    _local_address: str
    _username: str
    _peer_addresses: list[str]
    _room_code: str

    _pub_socket: zmq.Socket
    _sub_sockets: list[zmq.Socket]

    def __init__(
        self,
        local_address: str,
        username: str,
        peer_addresses: list[str],
        room_code: str,
        poller: zmq.Poller,
    ):
        context = zmq.Context.instance()

        self._local_address = local_address
        self._username = username
        self._room_code = room_code

        self._pub_socket = context.socket(zmq.PUB)
        self._pub_socket.bind(f"tcp://{self._local_address}")

        self._peer_addresses = []
        self._sub_sockets = []
        for peer_address in peer_addresses:
            sub_socket: zmq.Socket = context.socket(zmq.SUB)
            sub_socket.setsockopt(zmq.SUBSCRIBE, room_code.encode("ascii"))
            sub_socket.connect(f"tcp://{peer_address}")
            poller.register(sub_socket, zmq.POLLIN)

            self._sub_sockets.append(sub_socket)
            self._peer_addresses.append(peer_address)

    def is_in(self, events: dict) -> bool:
        for socket in self._sub_sockets:
            if socket in events:
                return True

        return False

    def read(self) -> list[MessageFrame]:
        messages = []

        for socket in self._sub_sockets:
            try:
                data = socket.recv(zmq.DONTWAIT)
                messages.append(MessageFrame.from_bytes(data))
            except zmq.ZMQError:
                # No new messages
                pass

        return messages

    def write_text(self, text: str):
        frame = MessageFrame(
            room_code=self._room_code,
            username_length=len(self._username),
            username=self._username,
            message_type=MessageFrame.MESSAGE_TEXT,
            data=text.encode("utf-8"),
        )

        self._pub_socket.send(frame.to_bytes())

    def write_audio(self, data: bytes):
        frame = MessageFrame(
            room_code=self._room_code,
            username_length=len(self._username),
            username=self._username,
            message_type=MessageFrame.MESSAGE_AUDIO,
            data=data,
        )

        self._pub_socket.send(frame.to_bytes())
