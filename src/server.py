#!/usr/bin/env python3
"""Exchange Server - entry point."""

import socket
import sys
import threading

from common import LineReader, send_line

# Shared state across all client threads — protected by state_lock.
state_lock = threading.Lock()
usernames = set()  # currently logged-in trader usernames


def handle_client(conn: socket.socket, addr):
    print(f"Client connected: {addr}")
    reader = LineReader(conn)
    my_username = None

    try:
        while True:
            line = reader.read_line()
            if line is None:
                print(f"Client {addr} disconnected.")
                break

            print(f"Received from {addr}: {line!r}")
            parts = line.split()
            if not parts:
                continue

            command = parts[0]

            if command == "LOGIN":
                if len(parts) != 2:
                    send_line(conn, "ERROR malformed LOGIN")
                    continue
                username = parts[1]
                with state_lock:
                    if username in usernames:
                        send_line(conn, "ERROR username taken")
                    else:
                        usernames.add(username)
                        my_username = username
                        send_line(conn, "OK")

            elif command == "QUIT":
                send_line(conn, "OK")
                break

            else:
                send_line(conn, f"ERROR unknown command {command}")

    finally:
        if my_username is not None:
            with state_lock:
                usernames.discard(my_username)
        conn.close()


def main():
    if len(sys.argv) != 3:
        print("Usage: server.py <host> <port>", file=sys.stderr)
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(20)  # backlog — allow several pending connections
    print(f"Exchange Server listening on {host}:{port}")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    main()