import argparse
from controller import run_main_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    def room_code_type(value: str):
        if len(value) != 5:
            raise argparse.ArgumentTypeError("Room code must be 5 characters long")

        return value

    parser.add_argument(
        "-r",
        "--room",
        type=room_code_type,
        required=True,
        help="Room code to connect to",
    )

    parser.add_argument(
        "-u",
        "--username",
        required=True,
        help="Username to be displayed in conversations",
    )

    parser.add_argument(
        "-p",
        "--peer",
        nargs="+",
        help="Peer's IP address and port (example: 192.168.0.20:2001)",
    )

    parser.add_argument(
        "-b",
        "--bind",
        nargs="?",
        default="0.0.0.0:2001",
        help="IP address and port to bind the app to",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    run_main_loop(
        local_address=args.bind,
        other_addresses=args.peer,
        username=args.username,
        room_code=args.room,
    )


if __name__ == "__main__":
    main()
