#!/usr/bin/env python3
"""
IndustryLab — Industrial Modbus/TCP Deep Packet Inspection (DPI) Proxy
Enforces IEC 62443 application-layer conduit filtering:
- Validates MBAP header and Modbus Function Codes (FC).
- Allows Read operations (FC 01, 02, 03, 04).
- Restricts Write operations (FC 05, 06, 15, 16) to authorized source IPs only.
- Returns Modbus exception 0x01 (Illegal Function) on unauthorized writes and logs alerts.
"""

import sys
import socket
import select
import logging
import argparse
from pathlib import Path

# Setup logging
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DPI_LOG_FILE = LOG_DIR / "modbus_dpi_audit.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DPI-FILTER] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DPI_LOG_FILE, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger("ModbusDPI")

READ_FUNCTION_CODES = {1, 2, 3, 4, 43}
WRITE_FUNCTION_CODES = {5, 6, 15, 16}

# Function names for readable logs
FC_NAMES = {
    1: "Read Coils",
    2: "Read Discrete Inputs",
    3: "Read Holding Registers",
    4: "Read Input Registers",
    5: "Write Single Coil",
    6: "Write Single Register",
    15: "Write Multiple Coils",
    16: "Write Multiple Registers",
    43: "Read Device Identification"
}


def parse_modbus_pdu(data: bytes):
    """
    Parses MBAP Header (7 bytes) and Modbus PDU:
    Bytes 0-1: Transaction ID
    Bytes 2-3: Protocol ID (0x0000)
    Bytes 4-5: Length
    Byte 6:    Unit ID
    Byte 7:    Function Code
    """
    if len(data) < 8:
        return None
    tx_id = int.from_bytes(data[0:2], byteorder='big')
    proto_id = int.from_bytes(data[2:4], byteorder='big')
    length = int.from_bytes(data[4:6], byteorder='big')
    unit_id = data[6]
    fc = data[7]
    return {
        "tx_id": tx_id,
        "proto_id": proto_id,
        "length": length,
        "unit_id": unit_id,
        "function_code": fc,
        "fc_name": FC_NAMES.get(fc, f"Unknown (0x{fc:02x})")
    }


def make_modbus_exception(tx_id: int, unit_id: int, fc: int, exception_code: int = 0x01) -> bytes:
    """Creates a standard Modbus TCP Exception response (Error FC = FC + 0x80)."""
    error_fc = (fc | 0x80) & 0xFF
    length = 3  # unit_id (1) + error_fc (1) + exception_code (1)
    return (
        tx_id.to_bytes(2, byteorder='big') +
        (0).to_bytes(2, byteorder='big') +
        length.to_bytes(2, byteorder='big') +
        bytes([unit_id, error_fc, exception_code])
    )


class ModbusDpiProxy:
    def __init__(self, listen_host="0.0.0.0", listen_port=1502, target_ip="127.0.0.1", target_port=502, authorized_write_ips=None):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_ip = target_ip
        self.target_port = target_port
        self.authorized_write_ips = set(authorized_write_ips or ["10.10.3.50", "127.0.0.1"])
        self.running = False
        self.total_packets_inspected = 0
        self.total_writes_blocked = 0

    def inspect_request(self, client_ip: str, data: bytes) -> tuple[bool, bytes | None]:
        """
        Inspects incoming client Modbus request.
        Returns: (allow_forward, optional_direct_response)
        """
        self.total_packets_inspected += 1
        pdu = parse_modbus_pdu(data)
        if not pdu:
            logger.warning(f"Malformed Modbus frame from {client_ip} (len={len(data)})")
            return False, None

        fc = pdu["function_code"]
        fc_name = pdu["fc_name"]

        # If it's a read operation, permit
        if fc in READ_FUNCTION_CODES:
            logger.debug(f"Permitted READ from {client_ip}: FC {fc} ({fc_name}) Unit {pdu['unit_id']}")
            return True, None

        # If it's a write operation, verify authorization
        if fc in WRITE_FUNCTION_CODES:
            if client_ip in self.authorized_write_ips:
                logger.info(f"Authorized WRITE from {client_ip}: FC {fc} ({fc_name}) Unit {pdu['unit_id']}")
                return True, None
            else:
                self.total_writes_blocked += 1
                logger.warning(
                    f"SECURITY ALERT [IEC62443-DPI-BLOCK]: Unauthorized WRITE attempt from {client_ip}! "
                    f"FC={fc} ({fc_name}) Unit={pdu['unit_id']}. Generating Exception 0x01 (Illegal Function)."
                )
                exc = make_modbus_exception(pdu["tx_id"], pdu["unit_id"], fc, exception_code=0x01)
                return False, exc

        # Unknown function code: Block by default
        logger.warning(f"Unknown Function Code {fc} from {client_ip}. Dropping.")
        exc = make_modbus_exception(pdu["tx_id"], pdu["unit_id"], fc, exception_code=0x01)
        return False, exc

    def handle_client(self, client_sock: socket.socket, client_addr: tuple):
        client_ip = client_addr[0]
        try:
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.settimeout(5.0)
            target_sock.connect((self.target_ip, self.target_port))
        except Exception as e:
            logger.error(f"Cannot connect to downstream PLC at {self.target_ip}:{self.target_port} - {e}")
            client_sock.close()
            return

        client_sock.setblocking(False)
        target_sock.setblocking(False)

        sockets = [client_sock, target_sock]
        buffer_size = 4096

        try:
            while self.running:
                r, _, _ = select.select(sockets, [], [], 1.0)
                if not r:
                    continue

                for s in r:
                    data = s.recv(buffer_size)
                    if not data:
                        return

                    if s is client_sock:
                        allow, exc_resp = self.inspect_request(client_ip, data)
                        if allow:
                            target_sock.sendall(data)
                        elif exc_resp:
                            client_sock.sendall(exc_resp)
                    else:
                        # Forward upstream PLC response back to client
                        client_sock.sendall(data)
        except Exception as e:
            logger.debug(f"Connection closed for {client_addr}: {e}")
        finally:
            client_sock.close()
            target_sock.close()

    def start(self):
        self.running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.listen_host, self.listen_port))
        server.listen(10)
        logger.info(f"Modbus DPI Proxy listening on {self.listen_host}:{self.listen_port} -> forwarding to {self.target_ip}:{self.target_port}")
        logger.info(f"Authorized Write IPs: {list(self.authorized_write_ips)}")

        try:
            while self.running:
                r, _, _ = select.select([server], [], [], 0.5)
                if r:
                    client_sock, client_addr = server.accept()
                    self.handle_client(client_sock, client_addr)
        except KeyboardInterrupt:
            logger.info("Shutting down DPI Proxy...")
        finally:
            server.close()


def main():
    parser = argparse.ArgumentParser(description="Modbus DPI Application Proxy")
    parser.add_argument("--listen-host", default="0.0.0.0", help="Listening address (default: 0.0.0.0)")
    parser.add_argument("--listen-port", type=int, default=1502, help="Listening port (default: 1502)")
    parser.add_argument("--target-ip", default="127.0.0.1", help="Target PLC IP (default: 127.0.0.1)")
    parser.add_argument("--target-port", type=int, default=502, help="Target PLC Port (default: 502)")
    parser.add_argument("--auth-ips", nargs="*", default=["10.10.3.50", "127.0.0.1"], help="Authorized IPs for Modbus writes")
    args = parser.parse_args()

    proxy = ModbusDpiProxy(
        listen_host=args.listen_host,
        listen_port=args.listen_port,
        target_ip=args.target_ip,
        target_port=args.target_port,
        authorized_write_ips=args.auth_ips
    )
    proxy.start()


if __name__ == "__main__":
    main()
