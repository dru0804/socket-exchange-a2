#!/usr/bin/env python3

import socket
import sys
import threading
from common import Linereader, sendl

def listen_for_messages(reader: Linereader):
    while True:
        line = reader.readl()
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
    reader = Linereader(sock)
    sendl(sock, f"LOGIN {username}")
    response = reader.readl()
    print(f"<< {response}")

    if response != "OK":
        print("Login failed, exiting.")
        sock.close()
        sys.exit(1)

    listener = threading.Thread(target=listen_for_messages, args=(reader,), daemon=True)
    listener.start()
    print("Connected. Commands: BUY <instr> <qty> <price> | SELL <instr> <qty> <price> | CANCEL <id> | QUIT")

    try:
        while True:
            line = input("> ")
            if not line.strip():
                continue
            sendl(sock, line)
            if line.strip().split()[0] == "QUIT":
                break
    except (EOFError, KeyboardInterrupt):
        try:
            sendl(sock, "QUIT")
        except OSError:
            pass
    finally:
        sock.close()

if __name__ == "__main__":
    main()