#!/usr/bin/env python3

import socket
import sys
import threading
import itertools

from common import Linereader, sendl

slock = threading.Lock()
usernames = set()            
tconns = {}               
orbook = []             
oridcount = itertools.count(1)
subscribers = {}            

INSTRUMENTS = {"JNST", "IMCT"}


def norder(orid, username, side, instrument, qty, price):
    return {
        "id": orid,
        "username": username,
        "side": side,         
        "instrument": instrument,
        "qty": qty,         
        "price": price,
    }


def match(nord):
    opp = "SELL" if nord["side"] == "BUY" else "BUY"

    for other in orbook:
        if other is nord or other["instrument"] != nord["instrument"] or other["side"] != opp or other["price"] != nord["price"] or other["qty"] <= 0 or nord["qty"] <= 0:
            continue

        tradq = min(other["qty"], nord["qty"])
        other["qty"] -= tradq
        nord["qty"] -= tradq
        instrument = nord["instrument"]
        price = nord["price"]
        buyord = nord if nord["side"] == "BUY" else other
        sellord = other if nord["side"] == "BUY" else nord
        bconn = tconns.get(buyord["username"])
        sconn = tconns.get(sellord["username"])

        if bconn is not None:
            try:
                sendl(bconn, f"BOUGHT {instrument} {tradq} {price}")
            except OSError:
                pass
        if sconn is not None:
            try:
                sendl(sconn, f"SOLD {instrument} {tradq} {price}")
            except OSError:
                pass
        broadcast(instrument, tradq, price)
        if nord["qty"] <= 0:
            break  
    orbook[:] = [o for o in orbook if o["qty"] > 0]

def broadcast(instrument, qty, price):
    for subconn in subscribers.get(instrument, ()):
        try:
            sendl(subconn, f"TRADE {instrument} {qty} {price}")
        except OSError:
            pass

def handletrad(conn, addr, reader, username):
    try:
        while True:
            line = reader.readl()
            if line is None:
                break

            print(f"Received from trader {username}: {line!r}")
            parts = line.split()
            if not parts:
                continue
            command = parts[0]
            MAX_VALUE = 2_147_483_647
            if command == "BUY" or command == "SELL":
                if len(parts) != 4:
                    sendl(conn, "ERROR malformed order")
                    continue
                _, instrument, qty_s, price_s = parts
                if instrument not in INSTRUMENTS:
                    sendl(conn, "ERROR unknown instrument")
                    continue
                try:
                    qty = int(qty_s)
                    price = int(price_s)
                except ValueError:
                    sendl(conn, "ERROR invalid quantity or price")
                    continue

                if not (1 <= qty <= MAX_VALUE) or not (1 <= price <= MAX_VALUE):
                    sendl(conn, "ERROR quantity or price out of range")
                    continue

                with slock:
                    orid = next(oridcount)
                    order = norder(orid, username, command, instrument, qty, price)
                    sendl(conn, f"ORDER_ACCEPTED {orid}")
                    orbook.append(order)
                    match(order)

            elif command == "CANCEL":
                if len(parts) != 2:
                    sendl(conn, "ERROR malformed cancel")
                    continue
                try:
                    tid = int(parts[1])
                except ValueError:
                    sendl(conn, "ERROR invalid order id")
                    continue

                with slock:
                    found = None
                    for o in orbook:
                        if o["id"] == tid and o["username"] == username:
                            found = o
                            break
                    if found is not None:
                        orbook.remove(found)
                        sendl(conn, f"ORDER_CANCELLED {tid}")
                    else:
                        sendl(conn, "ERROR no such order")
            elif command == "QUIT":
                sendl(conn, "OK")
                break
            else:
                sendl(conn, f"ERROR command not allowed for trader")
    finally:
        with slock:
            usernames.discard(username)
            tconns.pop(username, None)
        conn.close()
        print(f"Trader {username} ({addr}) disconnected.")

def handlemdata(conn, addr, reader):
    subs = set()
    try:
        while True:
            line = reader.readl()
            if line is None:
                break
            print(f"Received from market-data {addr}: {line!r}")
            parts = line.split()
            if not parts:
                continue
            command = parts[0]

            if command == "SUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    sendl(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with slock:
                    subscribers.setdefault(instrument, set()).add(conn)
                subs.add(instrument)
                sendl(conn, "OK")

            elif command == "UNSUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    sendl(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with slock:
                    subscribers.get(instrument, set()).discard(conn)
                subs.discard(instrument)
                sendl(conn, "OK")

            elif command == "QUIT":
                sendl(conn, "OK")
                break

            else:
                sendl(conn, "ERROR command not allowed for market-data client")

    finally:
        with slock:
            for instrument in subs:
                subscribers.get(instrument, set()).discard(conn)
        conn.close()
        print(f"Market-data client {addr} disconnected.")


def handlec(conn: socket.socket, addr):
    print(f"Client connected: {addr}")
    reader = Linereader(conn)
    first_line = reader.readl()
    if first_line is None:
        conn.close()
        return
    parts = first_line.split()
    if not parts:
        sendl(conn, "ERROR empty command")
        conn.close()
        return
    command = parts[0]
    if command == "LOGIN":
        if len(parts) != 2:
            sendl(conn, "ERROR malformed LOGIN")
            conn.close()
            return
        username = parts[1]
        with slock:
            if username in usernames:
                sendl(conn, "ERROR username taken")
                conn.close()
                return
            usernames.add(username)
            tconns[username] = conn
            sendl(conn, "OK")
        handletrad(conn, addr, reader, username)
    elif command == "SUBSCRIBE":
        if len(parts) != 2 or parts[1] not in INSTRUMENTS:
            sendl(conn, "ERROR unknown instrument")
            conn.close()
            return
        instrument = parts[1]
        with slock:
            subscribers.setdefault(instrument, set()).add(conn)
        sendl(conn, "OK")
        mdataafter1st(conn, addr, reader, {instrument})
    else:
        sendl(conn, "ERROR first message must be LOGIN or SUBSCRIBE")
        conn.close()

def mdataafter1st(conn, addr, reader, isubs):
    subs = set(isubs)
    try:
        while True:
            line = reader.readl()
            if line is None:
                break
            print(f"Received from market-data {addr}: {line!r}")
            parts = line.split()
            if not parts:
                continue
            command = parts[0]

            if command == "SUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    sendl(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with slock:
                    subscribers.setdefault(instrument, set()).add(conn)
                subs.add(instrument)
                sendl(conn, "OK")

            elif command == "UNSUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    sendl(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with slock:
                    subscribers.get(instrument, set()).discard(conn)
                subs.discard(instrument)
                sendl(conn, "OK")

            elif command == "QUIT":
                sendl(conn, "OK")
                break

            else:
                sendl(conn, "ERROR command not allowed for market-data client")

    finally:
        with slock:
            for instrument in subs:
                subscribers.get(instrument, set()).discard(conn)
        conn.close()
        print(f"Market-data client {addr} disconnected.")


def main():
    if len(sys.argv) != 3:
        print("Usage: server.py <host> <port>", file=sys.stderr)
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(20)
    print(f"Exchange Server listening on {host}:{port}")
    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handlec, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    main()