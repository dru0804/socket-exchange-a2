#!/usr/bin/env python3

import socket
import sys
import threading
from common import Linereader, sendl

def listrad(reader: Linereader):
    while True:
        line = reader.readl()
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
    reader = Linereader(sock)
    first_instrument = instruments[0]
    sendl(sock, f"SUBSCRIBE {first_instrument}")
    response = reader.readl()
    print(f"<< {response}")

    if response != "OK":
        print("Subscribe failed, exiting")
        sock.close()
        sys.exit(1)

    for instrument in instruments[1:]:
        sendl(sock, f"SUBSCRIBE {instrument}")
        response = reader.readl()
        print(f"<< {response}")

    listener = threading.Thread(target=listrad, args=(reader,), daemon=True)
    listener.start()
    print(f"Subscribed to {instruments}. Commands: SUBSCRIBE <instr> | UNSUBSCRIBE <instr> | QUIT")

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