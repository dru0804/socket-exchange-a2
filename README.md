# Socket Exchange - Assignment 2

## Team Members
- Drushya Salunke (2024cs10565)
- Sohana Kumar (2024cs10251)

## Programming Language and Runtime
- **Language**: Python 3
- **Runtime/Compiler**: Python 3 standard library. No external compilation step or dependencies are required.

## Build and Preparation
No compilation or build process is required since this is a Python-based implementation. 

Ensure that Python 3 is installed in your environment and that the launcher scripts (`server/run-server`, `client/run-trader`, `client/run-market-data`) are executable. If they are not executable, run:
```bash
chmod +x server/run-server client/run-trader client/run-market-data
```

## How to Start the Exchange Server
You can start the exchange server using the provided launcher script:
```bash
./server/run-server <host> <port>
```
Alternatively, you can run it directly using Python:
```bash
python3 src/server.py <host> <port>
```
Example:
```bash
./server/run-server 127.0.0.1 5000
```

## How to Start the Clients

### Trader Client
You can start a trader client using the provided launcher script:
```bash
./client/run-trader <host> <port> <username>
```
Alternatively, you can run it directly:
```bash
python3 src/trader.py <host> <port> <username>
```
Example:
```bash
./client/run-trader 127.0.0.1 5000 alice
```

### Market-Data Client
You can start a market-data client using the provided launcher script. You must specify at least one instrument to subscribe to (e.g., JNST, IMCT). You can optionally provide multiple instruments.
```bash
./client/run-market-data <host> <port> <instrument> [instrument2 ...]
```
Alternatively, you can run it directly:
```bash
python3 src/market_data.py <host> <port> <instrument> [instrument2 ...]
```
Example:
```bash
./client/run-market-data 127.0.0.1 5000 JNST IMCT
```

## Configuration Required
- **Python 3**: The system expects `python3` to be available in your PATH.
- **Concurrency**: The server handles multiple concurrent clients using Python's `threading` module (a thread-per-connection model).
- **External Dependencies**: None. The implementation relies solely on the Python Standard Library (e.g., `socket`, `threading`, `sys`).
