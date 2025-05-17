import zmq
from threading import Thread
from audio import AudioManager
from message import MessageFrame
from network import NetworkManager
from text import TextManager


def run_main_loop(
    local_address: str, other_addresses: list[str], username: str, room_code: str
):
    poller = zmq.Poller()

    network_manager = NetworkManager(
        local_address=local_address,
        username=username,
        peer_addresses=other_addresses,
        room_code=room_code,
        poller=poller,
    )
    text_manager = TextManager(username, poller)
    audio_manager = AudioManager(poller)

    def _main_loop():
        running = True
        while running:
            events = dict(poller.poll(timeout=500))

            if network_manager.is_in(events):
                msgs = network_manager.read()
                for msg in msgs:
                    if msg.message_type == MessageFrame.MESSAGE_AUDIO:
                        audio_manager.write(msg.data)
                    else:
                        text_manager.write(msg.username, msg.data.decode("utf-8"))

            if text_manager.is_in(events):
                msg = text_manager.read()
                network_manager.write_text(msg)

            if audio_manager.is_in(events):
                data = audio_manager.read()
                network_manager.write_audio(data)

            if text_manager.user_has_quit():
                running = False

    controller_thread = Thread(target=_main_loop)
    controller_thread.start()

    # TUI must be run in main thread
    text_manager.run_app(username)

    audio_manager.stop()
