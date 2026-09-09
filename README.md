# Socket Exchange - Assignment 2

## Team Members
- Drushya Salunke (2024cs10565)
- Sohana Kumar (2024cs10251)

## Programming Language and Runtime
- **Language**: Python 3
- **Runtime/Compiler**: Python 3 standard library. No external compilation steps or dependencies are required.

## Build and Preparation
No compilation or build process is required for this Python-based implementation. 

Ensure that Python 3 is installed in your environment and that the launcher scripts are executable. If they are not executable, run the following command:
```bash
chmod +x server/run-server client/run-trader client/run-market-data
```

## How to Start the Exchange Server
Start the exchange server using the provided launcher script:
```bash
./server/run-server <host> <port>
```
Alternatively, you can run the source file directly:
```bash
python3 src/server.py <host> <port>
```
Example:
```bash
./server/run-server 127.0.0.1 5000
```

## How to Start the Clients

### Trader Client
Start a trader client using the provided launcher script:
```bash
./client/run-trader <host> <port> <username>
```
Alternatively, you can run the source file directly:
```bash
python3 src/trader.py <host> <port> <username>
```
Example:
```bash
./client/run-trader 127.0.0.1 5000 alice
```

### Market-Data Client
Start a market-data client using the provided launcher script. You must specify at least one instrument to subscribe to (e.g., JNST, IMCT), with optional additional instruments:
```bash
./client/run-market-data <host> <port> <instrument> [instrument2 ...]
```
Alternatively, you can run the source file directly:
```bash
python3 src/market_data.py <host> <port> <instrument> [instrument2 ...]
```
Example:
```bash
./client/run-market-data 127.0.0.1 5000 JNST IMCT
```

## Configuration
- **Python 3**: The system expects `python3` to be available in your system path.
- **Concurrency**: The server handles multiple concurrent clients using Python's `threading` module via a thread-per-connection model.
- **External Dependencies**: None. The implementation relies entirely on the built-in Python Standard Library (e.g., `socket`, `threading`, `sys`).
