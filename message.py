from dataclasses import dataclass
from typing import Self


@dataclass
class MessageFrame:
    MESSAGE_TEXT = 0
    MESSAGE_AUDIO = 1
    MESSAGE_VIDEO = 2

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
