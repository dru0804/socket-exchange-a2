"""Throwaway test: proves LineReader correctly reassembles a message
sent in several pieces, and correctly separates multiple messages
sent in one burst."""

import socket
import threading
import time
import sys

sys.path.insert(0, "src")
from common import LineReader

HOST = "127.0.0.1"
PORT = 5050


def server_thread():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    conn, _ = srv.accept()
    reader = LineReader(conn)

    # Should correctly get back "LOGIN alice" even though it was sent
    # in 4 separate pieces.
    line1 = reader.read_line()
    print("Server received message 1:", repr(line1))

    # Should correctly split "BUY JNST 100 238" and "SELL JNST 50 238"
    # even though both arrived in a single recv().
    line2 = reader.read_line()
    print("Server received message 2:", repr(line2))
    line3 = reader.read_line()
    print("Server received message 3:", repr(line3))

    conn.close()
    srv.close()


t = threading.Thread(target=server_thread)
t.start()
time.sleep(0.3)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

# Send one message in 4 tiny separate pieces.
for piece in [b"LOGIN ", b"ali", b"ce", b"\n"]:
    client.send(piece)
    time.sleep(0.1)

# Send two full messages in a single burst.
client.send(b"BUY JNST 100 238\nSELL JNST 50 238\n")

time.sleep(0.5)
client.close()
t.join()