from typing import Self
import zmq

from ipaddress import ip_address, IPv4Address, IPv6Address

import sys
from threading import Thread
from dataclasses import dataclass

from message import MessageFrame


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
            message_type=MessageFrame.MESSAGE_TEXT,
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
