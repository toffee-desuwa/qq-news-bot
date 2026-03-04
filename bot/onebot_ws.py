"""OneBot v11 WebSocket client with reconnect logic.

Implements a minimal RFC 6455 WebSocket client using only stdlib.
Reconnects with exponential backoff capped at 60s.
"""

import base64
import json
import os
import secrets
import socket
import ssl
import struct
import time
from typing import Callable, Optional
from urllib.parse import urlparse


class OneBotWS:
    """Minimal OneBot v11 WebSocket client (stdlib only).

    Implements just enough of RFC 6455 to send/receive JSON text frames.
    """

    def __init__(
        self,
        url: str = "",
        access_token: str = "",
        on_message: Optional[Callable[[dict], None]] = None,
    ):
        self.url = url or os.environ.get("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
        self.access_token = access_token or os.environ.get(
            "ONEBOT_ACCESS_TOKEN", ""
        )
        self.on_message = on_message
        self._sock: Optional[socket.socket] = None
        self._running = False

    # -- public API -----------------------------------------------------------

    def run_forever(self) -> None:
        """Connect and read messages in a loop, reconnecting on failure."""
        self._running = True
        backoff = 1
        while self._running:
            try:
                self._connect()
                backoff = 1
                self._read_loop()
            except (OSError, ConnectionError, ValueError) as exc:
                print(f"[ws] connection error: {exc}")
            finally:
                self._close_sock()
            if not self._running:
                break
            print(f"[ws] reconnecting in {backoff}s ...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

    def stop(self) -> None:
        self._running = False
        self._close_sock()

    def send_group_msg(self, group_id: int, message: str) -> None:
        """Send a text message to a group via OneBot send_group_msg action."""
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": group_id,
                "message": message,
            },
        }
        self._send_json(payload)

    # -- WebSocket handshake (RFC 6455) ---------------------------------------

    def _connect(self) -> None:
        parsed = urlparse(self.url)
        use_ssl = parsed.scheme in ("wss", "https")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if use_ssl else 80)
        path = parsed.path or "/"

        raw = socket.create_connection((host, port), timeout=10)
        if use_ssl:
            ctx = ssl.create_default_context()
            raw = ctx.wrap_socket(raw, server_hostname=host)
        self._sock = raw

        ws_key = base64.b64encode(secrets.token_bytes(16)).decode()
        headers = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
        )
        if self.access_token:
            headers += f"Authorization: Bearer {self.access_token}\r\n"
        headers += "\r\n"

        self._sock.sendall(headers.encode())

        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("connection closed during handshake")
            resp += chunk
        status_line = resp.split(b"\r\n")[0].decode()
        if "101" not in status_line:
            raise ConnectionError(f"handshake failed: {status_line}")
        print(f"[ws] connected to {self.url}")

    # -- frame read/write (minimal RFC 6455) ----------------------------------

    def _read_loop(self) -> None:
        while self._running and self._sock:
            opcode, data = self._read_frame()
            if opcode == 0x8:  # close
                break
            if opcode == 0x9:  # ping
                self._send_frame(0xA, data)  # pong
                continue
            if opcode == 0x1 and self.on_message:  # text
                try:
                    msg = json.loads(data.decode("utf-8"))
                    self.on_message(msg)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

    def _read_frame(self) -> tuple:
        header = self._recv_exact(2)
        opcode = header[0] & 0x0F
        masked = bool(header[1] & 0x80)
        length = header[1] & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]

        if masked:
            mask_key = self._recv_exact(4)
            raw = self._recv_exact(length)
            data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(raw))
        else:
            data = self._recv_exact(length)

        return opcode, data

    def _send_frame(self, opcode: int, data: bytes) -> None:
        mask_key = secrets.token_bytes(4)
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))

        frame = bytearray()
        frame.append(0x80 | opcode)

        length = len(data)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack("!H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack("!Q", length))

        frame.extend(mask_key)
        frame.extend(masked)

        if self._sock:
            self._sock.sendall(frame)

    def _send_json(self, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send_frame(0x1, data)

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            if not self._sock:
                raise ConnectionError("socket closed")
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection lost")
            buf.extend(chunk)
        return bytes(buf)

    def _close_sock(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
