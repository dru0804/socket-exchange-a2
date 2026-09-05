"""Shared helpers for line-based TCP protocol framing."""

import socket


class LineReader:
    """
    Wraps a socket and yields complete newline-terminated application
    messages, correctly handling:
      - one message split across multiple recv() calls
      - multiple messages returned by a single recv() call
      - arbitrary split points in the byte stream
    """

    def __init__(self, sock: socket.socket, bufsize: int = 4096):
        self.sock = sock
        self.bufsize = bufsize
        self._buffer = b""

    def read_line(self):
        """
        Return the next complete message (without the trailing '\\n'),
        or None if the connection was closed cleanly (recv returned b"").
        Raises OSError if the underlying recv() fails.
        """
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(self.bufsize)
            if not chunk:
                # Connection closed. If there's leftover data with no
                # newline, we discard it (incomplete final message).
                return None
            self._buffer += chunk

        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode("utf-8", errors="replace")


def send_line(sock: socket.socket, message: str) -> None:
    """Send one complete newline-terminated application message,
    handling partial writes."""
    data = (message + "\n").encode("utf-8")
    view = memoryview(data)
    while view:
        sent = sock.send(view)
        if sent <= 0:
            raise RuntimeError("send() made no progress")
        view = view[sent:]