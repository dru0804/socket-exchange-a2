#!/usr/bin/env python3
"""Market-Data Client - entry point."""

import socket
import sys
import threading

from common import LineReader, send_line


def listen_for_trades(reader: LineReader):
    """Background thread: continuously print incoming TRADE broadcasts
    and any other server messages."""
    while True:
        line = reader.read_line()
        if line is None:
            print("\n[Disconnected from server]")
            break
        print(f"\n<< {line}")
        print("> ", end="", flush=True)


def main():
    if len(sys.argv) < 4:
        print("Usage: market_data.py <host> <port> <instrument> [instrument2 ...]", file=sys.stderr)
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    instruments = sys.argv[3:]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    reader = LineReader(sock)

    # First message must be SUBSCRIBE to identify as a Market-Data client.
    first_instrument = instruments[0]
    send_line(sock, f"SUBSCRIBE {first_instrument}")
    response = reader.read_line()
    print(f"<< {response}")

    if response != "OK":
        print("Subscribe failed, exiting.")
        sock.close()
        sys.exit(1)

    # Subscribe to any additional instruments given on the command line.
    for instrument in instruments[1:]:
        send_line(sock, f"SUBSCRIBE {instrument}")
        response = reader.read_line()
        print(f"<< {response}")

    listener = threading.Thread(target=listen_for_trades, args=(reader,), daemon=True)
    listener.start()

    print(f"Subscribed to {instruments}. Commands: SUBSCRIBE <instr> | UNSUBSCRIBE <instr> | QUIT")

    try:
        while True:
            line = input("> ")
            if not line.strip():
                continue
            send_line(sock, line)
            if line.strip().split()[0] == "QUIT":
                break
    except (EOFError, KeyboardInterrupt):
        try:
            send_line(sock, "QUIT")
        except OSError:
            pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()