import zmq
import sys

from comms import Sender, Receiver
from text import TextReader


def main():
    context = zmq.Context.instance()

    my_port = sys.argv[1]
    partner_port = sys.argv[2]
    username = sys.argv[3]
    room_code = "teste"

    sender = Sender("0.0.0.0", my_port, room_code, username)
    receiver = Receiver("127.0.0.1", partner_port, room_code)

    text = TextReader()

    poller = zmq.Poller()
    poller.register(receiver.socket, zmq.POLLIN)
    poller.register(text.socket, zmq.POLLIN)

    while True:
        events = dict(poller.poll())

        if receiver.socket in events:
            msg = receiver.receive_message()
            print(msg)

        if text.socket in events:
            msg = text.socket.recv_string()
            sender.send_text(msg)


if __name__ == "__main__":
    main()
