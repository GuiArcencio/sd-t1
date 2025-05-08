from typing import Self
import zmq

from ipaddress import ip_address, IPv4Address, IPv6Address

import sys
from threading import Thread
from dataclasses import dataclass

MESSAGE_TEXT = 0
MESSAGE_AUDIO = 1
MESSAGE_VIDEO = 2


@dataclass
class MessageFrame:
    room_code: str  # 5 bytes
    username_length: int  # 1 byte
    username: str  # {username_length} bytes
    message_type: int  # 1 byte
    data: bytes

    @classmethod
    def from_bytes(cls, frame: bytes) -> Self | None:
        try:
            room_code = frame[0:5].decode("ascii")
            frame = frame[5:]

            username_length = int(frame[0])
            frame = frame[1:]

            username = frame[:username_length].decode("ascii")
            frame = frame[username_length:]

            message_type = int(frame[0])

            data = frame[1:]

            return cls(
                room_code=room_code,
                username_length=username_length,
                username=username,
                message_type=message_type,
                data=data,
            )
        except:
            return None  # Invalid message

    def to_bytes(self) -> bytes:
        frame = self.room_code.encode("ascii")
        frame += self.username_length.to_bytes(1)
        frame += self.username.encode("ascii")
        frame += self.message_type.to_bytes(1)
        frame += self.data

        return frame


class Sender:
    ip_addr: IPv4Address | IPv6Address
    port: int
    room_code: str
    username: str
    socket: zmq.Socket

    def __init__(
        self,
        ip_addr: str | int,
        port: str | int,
        room_code: str,
        username: str,
        context: zmq.Context = None,
    ):
        context = context or zmq.Context.instance()

        self.ip_addr = ip_address(ip_addr)
        self.port = int(port)
        self.room_code = room_code
        self.username = username

        self.socket = context.socket(zmq.PUB)
        self.socket.bind(f"tcp://{self.ip_addr}:{self.port}")

    def send_text(self, text: str):
        frame = MessageFrame(
            room_code=self.room_code,
            username_length=len(self.username),
            username=self.username,
            message_type=MESSAGE_TEXT,
            data=text.encode("utf-8"),
        )

        self.socket.send(frame.to_bytes())


class Receiver:
    ip_addr: IPv4Address | IPv6Address
    port: int
    room_code: str
    socket: zmq.Socket

    def __init__(
        self,
        ip_addr: str | int,
        port: str | int,
        room_code: str,
        context: zmq.Context = None,
    ):
        context = context or zmq.Context.instance()

        self.ip_addr = ip_address(ip_addr)
        self.port = int(port)
        self.room_code = room_code
        self.socket = context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.SUBSCRIBE, room_code.encode("ascii"))
        self.socket.connect(f"tcp://{self.ip_addr}:{self.port}")

    def receive_message(self) -> MessageFrame | None:
        try:
            data = self.socket.recv(zmq.NOBLOCK)
        except zmq.ZMQError:
            # No new messages
            return None

        return MessageFrame.from_bytes(data)


def keyboard_reader(context: zmq.Context = None):
    context = context or zmq.Context.instance()

    socket: zmq.Socket = context.socket(zmq.PAIR)
    socket.connect("inproc://keyboard")

    while True:
        message = input()
        if message:
            socket.send_string(message)


def main():
    context = zmq.Context.instance()

    keyboard_socket: zmq.Socket = context.socket(zmq.PAIR)
    keyboard_socket.bind("inproc://keyboard")

    my_port = sys.argv[1]
    partner_port = sys.argv[2]
    username = sys.argv[3]
    room_code = "teste"

    sender = Sender("0.0.0.0", my_port, room_code, username)
    receiver = Receiver("127.0.0.1", partner_port, room_code)

    keyboard_thread = Thread(target=keyboard_reader)
    keyboard_thread.start()

    poller = zmq.Poller()
    poller.register(receiver.socket, zmq.POLLIN)
    poller.register(keyboard_socket, zmq.POLLIN)

    while True:
        events = dict(poller.poll())

        if receiver.socket in events:
            msg = receiver.receive_message()
            print(msg)

        if keyboard_socket in events:
            msg = keyboard_socket.recv_string()
            sender.send_text(msg)


if __name__ == "__main__":
    main()
