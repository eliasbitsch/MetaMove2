#!/usr/bin/env python3
"""TCP echo server for RAPID-TCP-Bridge latency measurement.

RAPID sends 'S <seq> <ts_ms>\\n' on port 7000.
This server echoes back 'T <seq> <ts_ms>\\n' immediately.
RAPID computes RTT = current_ts - ts_ms_in_echoed_frame.

Run:
    python tcp_echo_probe.py
Then start MetaMoveCoreTCP.main on the VC.
"""
import socket
import time
import threading

HOST = "0.0.0.0"
PORT = 7000


def handle_client(conn: socket.socket, addr) -> None:
    print(f"[echo] client connected: {addr}")
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    buf = b""
    n_frames = 0
    t0 = time.time()
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line.startswith(b"S "):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                seq, ts_ms = parts[1].decode(), parts[2].decode()
                reply = f"T {seq} {ts_ms}\n".encode()
                conn.sendall(reply)
                n_frames += 1
                if n_frames % 100 == 0:
                    elapsed = time.time() - t0
                    print(f"[echo] {n_frames} frames echoed ({n_frames/elapsed:.0f} Hz)")
    except ConnectionResetError:
        pass
    finally:
        conn.close()
        elapsed = time.time() - t0
        print(f"[echo] client {addr} done: {n_frames} frames in {elapsed:.1f}s ({n_frames/max(elapsed,0.001):.0f} Hz)")


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print(f"[echo] listening on {HOST}:{PORT}")
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
