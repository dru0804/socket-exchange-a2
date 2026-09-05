#!/usr/bin/env python3
"""Exchange Server - entry point."""

import socket
import sys
import threading
import itertools

from common import LineReader, send_line

# ---------------------------------------------------------------------
# Shared state — all protected by state_lock
# ---------------------------------------------------------------------
state_lock = threading.Lock()
usernames = set()                 # currently logged-in trader usernames
trader_conns = {}                 # username -> socket connection
order_book = []                   # list of order dicts (see below)
order_id_counter = itertools.count(1)
subscribers = {}                  # instrument -> set of market-data sockets

INSTRUMENTS = {"JNST", "IMCT"}


def new_order(order_id, username, side, instrument, qty, price):
    return {
        "id": order_id,
        "username": username,
        "side": side,          # "BUY" or "SELL"
        "instrument": instrument,
        "qty": qty,            # remaining quantity
        "price": price,
    }


def try_match(new_order_dict):
    """
    Attempt to match new_order_dict against the book. Sends BOUGHT/SOLD
    to affected traders and TRADE to subscribers as matches occur.
    Must be called while holding state_lock.
    """
    opposite_side = "SELL" if new_order_dict["side"] == "BUY" else "BUY"

    for other in order_book:
        if other is new_order_dict:
            continue
        if other["instrument"] != new_order_dict["instrument"]:
            continue
        if other["side"] != opposite_side:
            continue
        if other["price"] != new_order_dict["price"]:
            continue
        if other["qty"] <= 0 or new_order_dict["qty"] <= 0:
            continue

        traded_qty = min(other["qty"], new_order_dict["qty"])
        other["qty"] -= traded_qty
        new_order_dict["qty"] -= traded_qty

        instrument = new_order_dict["instrument"]
        price = new_order_dict["price"]

        buy_order = new_order_dict if new_order_dict["side"] == "BUY" else other
        sell_order = other if new_order_dict["side"] == "BUY" else new_order_dict

        buyer_conn = trader_conns.get(buy_order["username"])
        seller_conn = trader_conns.get(sell_order["username"])

        if buyer_conn is not None:
            try:
                send_line(buyer_conn, f"BOUGHT {instrument} {traded_qty} {price}")
            except OSError:
                pass
        if seller_conn is not None:
            try:
                send_line(seller_conn, f"SOLD {instrument} {traded_qty} {price}")
            except OSError:
                pass

        broadcast_trade(instrument, traded_qty, price)

        if new_order_dict["qty"] <= 0:
            break  # fully filled, stop matching this order

    # Remove fully-filled orders from the book.
    order_book[:] = [o for o in order_book if o["qty"] > 0]


def broadcast_trade(instrument, qty, price):
    """Must be called while holding state_lock."""
    for sub_conn in subscribers.get(instrument, ()):
        try:
            send_line(sub_conn, f"TRADE {instrument} {qty} {price}")
        except OSError:
            pass


def handle_trader(conn, addr, reader, username):
    """Main loop once a client has identified as a Trader via LOGIN."""
    try:
        while True:
            line = reader.read_line()
            if line is None:
                break

            print(f"Received from trader {username}: {line!r}")
            parts = line.split()
            if not parts:
                continue
            command = parts[0]

            if command == "BUY" or command == "SELL":
                if len(parts) != 4:
                    send_line(conn, "ERROR malformed order")
                    continue
                _, instrument, qty_s, price_s = parts
                if instrument not in INSTRUMENTS:
                    send_line(conn, "ERROR unknown instrument")
                    continue
                try:
                    qty = int(qty_s)
                    price = int(price_s)
                    if qty <= 0 or price <= 0:
                        raise ValueError
                except ValueError:
                    send_line(conn, "ERROR invalid quantity or price")
                    continue

                with state_lock:
                    order_id = next(order_id_counter)
                    order = new_order(order_id, username, command, instrument, qty, price)
                    send_line(conn, f"ORDER_ACCEPTED {order_id}")
                    order_book.append(order)
                    try_match(order)

            elif command == "CANCEL":
                if len(parts) != 2:
                    send_line(conn, "ERROR malformed cancel")
                    continue
                try:
                    target_id = int(parts[1])
                except ValueError:
                    send_line(conn, "ERROR invalid order id")
                    continue

                with state_lock:
                    found = None
                    for o in order_book:
                        if o["id"] == target_id and o["username"] == username:
                            found = o
                            break
                    if found is not None:
                        order_book.remove(found)
                        send_line(conn, f"ORDER_CANCELLED {target_id}")
                    else:
                        send_line(conn, "ERROR no such order")

            elif command == "QUIT":
                send_line(conn, "OK")
                break

            else:
                send_line(conn, f"ERROR command not allowed for trader")

    finally:
        with state_lock:
            usernames.discard(username)
            trader_conns.pop(username, None)
        conn.close()
        print(f"Trader {username} ({addr}) disconnected.")


def handle_market_data(conn, addr, reader):
    """Main loop once a client has identified as Market-Data via SUBSCRIBE."""
    my_subscriptions = set()
    try:
        while True:
            line = reader.read_line()
            if line is None:
                break

            print(f"Received from market-data {addr}: {line!r}")
            parts = line.split()
            if not parts:
                continue
            command = parts[0]

            if command == "SUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    send_line(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with state_lock:
                    subscribers.setdefault(instrument, set()).add(conn)
                my_subscriptions.add(instrument)
                send_line(conn, "OK")

            elif command == "UNSUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    send_line(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with state_lock:
                    subscribers.get(instrument, set()).discard(conn)
                my_subscriptions.discard(instrument)
                send_line(conn, "OK")

            elif command == "QUIT":
                send_line(conn, "OK")
                break

            else:
                send_line(conn, "ERROR command not allowed for market-data client")

    finally:
        with state_lock:
            for instrument in my_subscriptions:
                subscribers.get(instrument, set()).discard(conn)
        conn.close()
        print(f"Market-data client {addr} disconnected.")


def handle_client(conn: socket.socket, addr):
    print(f"Client connected: {addr}")
    reader = LineReader(conn)

    # The first message determines the client's role:
    #   LOGIN <username>      -> Trader Client
    #   SUBSCRIBE <instrument> -> Market-Data Client
    first_line = reader.read_line()
    if first_line is None:
        conn.close()
        return

    parts = first_line.split()
    if not parts:
        send_line(conn, "ERROR empty command")
        conn.close()
        return

    command = parts[0]

    if command == "LOGIN":
        if len(parts) != 2:
            send_line(conn, "ERROR malformed LOGIN")
            conn.close()
            return
        username = parts[1]
        with state_lock:
            if username in usernames:
                send_line(conn, "ERROR username taken")
                conn.close()
                return
            usernames.add(username)
            trader_conns[username] = conn
            send_line(conn, "OK")
        handle_trader(conn, addr, reader, username)

    elif command == "SUBSCRIBE":
        if len(parts) != 2 or parts[1] not in INSTRUMENTS:
            send_line(conn, "ERROR unknown instrument")
            conn.close()
            return
        instrument = parts[1]
        with state_lock:
            subscribers.setdefault(instrument, set()).add(conn)
        send_line(conn, "OK")
        handle_market_data_after_first(conn, addr, reader, {instrument})

    else:
        send_line(conn, "ERROR first message must be LOGIN or SUBSCRIBE")
        conn.close()


def handle_market_data_after_first(conn, addr, reader, initial_subs):
    """Same as handle_market_data but the first SUBSCRIBE was already
    processed as the role-determining message."""
    my_subscriptions = set(initial_subs)
    try:
        while True:
            line = reader.read_line()
            if line is None:
                break
            print(f"Received from market-data {addr}: {line!r}")
            parts = line.split()
            if not parts:
                continue
            command = parts[0]

            if command == "SUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    send_line(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with state_lock:
                    subscribers.setdefault(instrument, set()).add(conn)
                my_subscriptions.add(instrument)
                send_line(conn, "OK")

            elif command == "UNSUBSCRIBE":
                if len(parts) != 2 or parts[1] not in INSTRUMENTS:
                    send_line(conn, "ERROR unknown instrument")
                    continue
                instrument = parts[1]
                with state_lock:
                    subscribers.get(instrument, set()).discard(conn)
                my_subscriptions.discard(instrument)
                send_line(conn, "OK")

            elif command == "QUIT":
                send_line(conn, "OK")
                break

            else:
                send_line(conn, "ERROR command not allowed for market-data client")

    finally:
        with state_lock:
            for instrument in my_subscriptions:
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
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    main()