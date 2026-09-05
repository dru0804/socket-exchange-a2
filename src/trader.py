#!/usr/bin/env python3
"""Trader Client - entry point."""

import socket
import sys
import threading

from common import LineReader, send_line


def listen_for_messages(reader: LineReader):
    """Background thread: continuously read and print server messages
    that arrive after login (BOUGHT, SOLD, ERROR, ORDER_ACCEPTED, etc.)."""
    while True:
        line = reader.read_line()
        if line is None:
            print("\n[Disconnected from server]")
            break
        print(f"\n<< {line}")
        print("> ", end="", flush=True)


def main():
    if len(sys.argv) != 4:
        print("Usage: trader.py <host> <port> <username>", file=sys.stderr)
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    reader = LineReader(sock)

    # First message must be LOGIN to identify as a Trader.
    send_line(sock, f"LOGIN {username}")
    response = reader.read_line()
    print(f"<< {response}")

    if response != "OK":
        print("Login failed, exiting.")
        sock.close()
        sys.exit(1)

    # Use the SAME reader (and its buffer) in the background thread, so no
    # bytes are lost or double-read between the login response and
    # subsequent async messages.
    listener = threading.Thread(target=listen_for_messages, args=(reader,), daemon=True)
    listener.start()

    print("Connected. Commands: BUY <instr> <qty> <price> | SELL <instr> <qty> <price> | CANCEL <id> | QUIT")

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