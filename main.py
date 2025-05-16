import zmq
import sys

from audio import AudioManager
from message import MessageFrame
from network import NetworkManager
from text import TextManager


def main():
    context = zmq.Context.instance()

    my_address = sys.argv[1]
    other_address = sys.argv[2]
    username = sys.argv[3]
    room_code = "teste"

    poller = zmq.Poller()

    network_manager = NetworkManager(
        local_address=my_address,
        username=username,
        peer_addresses=[other_address],
        room_code=room_code,
        poller=poller,
    )
    text_manager = TextManager(poller)
    audio_manager = AudioManager(poller)

    while True:
        events = dict(poller.poll())

        if network_manager.is_in(events):
            msgs = network_manager.read()
            for msg in msgs:
                if msg.message_type == MessageFrame.MESSAGE_AUDIO:
                    audio_manager.write(msg.data)
                else:
                    text_manager.write(f"{msg.username}> {msg.data.decode()}")

        if text_manager.is_in(events):
            msg = text_manager.read()
            network_manager.write_text(msg)

        if audio_manager.is_in(events):
            data = audio_manager.read()
            network_manager.write_audio(data)


if __name__ == "__main__":
    main()
