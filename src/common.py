import socket

class Linereader:
    def __init__(self, sock: socket.socket, bufsize: int = 4096):
        self.sock = sock
        self.bufsize = bufsize
        self._buffer = b""

    def readl(self):
        while b"\n" not in self._buffer:
            try:
                chunk = self.sock.recv(self.bufsize)
            except ConnectionResetError:
                return None
            if not chunk:
                return None
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode("utf-8", errors="replace")

def sendl(sock: socket.socket, message: str) -> None:
    data = (message + "\n").encode("utf-8")
    view = memoryview(data)
    while view:
        sent = sock.send(view)
        if sent <= 0:
            raise RuntimeError("send() made no progress")
        view = view[sent:]