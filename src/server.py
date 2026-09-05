#!/usr/bin/env python3
"""Exchange Server - entry point."""

import socket
import sys

from common import LineReader, send_line


def handle_client(conn: socket.socket, addr):
    print(f"Client connected: {addr}")
    reader = LineReader(conn)

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
            # TODO: validate username, check uniqueness
            send_line(conn, "OK")
        elif command == "QUIT":
            send_line(conn, "OK")
            break
        else:
            send_line(conn, f"ERROR unknown command {command}")

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
    srv.listen(5)
    print(f"Exchange Server listening on {host}:{port}")

    while True:
        conn, addr = srv.accept()
        handle_client(conn, addr)  # one client at a time for now


if __name__ == "__main__":
    main()