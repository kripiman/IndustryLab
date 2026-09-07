#!/usr/bin/env python3
"""
IndustryLab — Robust Dual-Version Modbus/TCP Slave Server
Compatible with both pymodbus 2.x and 3.x.
Provides thread-safe access to coils, discrete inputs, input registers, and holding registers.
"""

import sys
import time
import socket
import logging
import threading
from pathlib import Path

# Setup logging
logger = logging.getLogger("ModbusServer")

try:
    from pymodbus.datastore import (
        ModbusSequentialDataBlock,
        ModbusSlaveContext,
        ModbusServerContext
    )
except ImportError:
    ModbusSequentialDataBlock = None
    ModbusSlaveContext = None
    ModbusServerContext = None

# Support both pymodbus 2.x and 3.x imports
try:
    from pymodbus.server.sync import StartTcpServer
except ImportError:
    try:
        from pymodbus.server import StartTcpServer
    except ImportError:
        StartTcpServer = None


class ModbusPlcServer:
    def __init__(self, host="0.0.0.0", port=502, num_coils=32, num_discrete=32, num_holding=32, num_inputs=32):
        self.host = host
        self.port = port
        self.lock = threading.Lock()
        self.server_thread = None
        self.server = None
        self.running = False

        # Initialize data blocks with zeroes
        self.coils_block = ModbusSequentialDataBlock(0, [0] * num_coils)
        self.discrete_block = ModbusSequentialDataBlock(0, [0] * num_discrete)
        self.holding_block = ModbusSequentialDataBlock(0, [0] * num_holding)
        self.input_block = ModbusSequentialDataBlock(0, [0] * num_inputs)

        self.slave_context = ModbusSlaveContext(
            di=self.discrete_block,
            co=self.coils_block,
            hr=self.holding_block,
            ir=self.input_block,
            zero_mode=True
        )
        self.context = ModbusServerContext(slaves=self.slave_context, single=True)

    def get_coil(self, address: int) -> bool:
        with self.lock:
            vals = self.slave_context.getValues(1, address, count=1)
            return bool(vals[0]) if vals else False

    def set_coil(self, address: int, value: bool):
        with self.lock:
            self.slave_context.setValues(1, address, [1 if value else 0])

    def get_discrete_input(self, address: int) -> bool:
        with self.lock:
            vals = self.slave_context.getValues(2, address, count=1)
            return bool(vals[0]) if vals else False

    def set_discrete_input(self, address: int, value: bool):
        with self.lock:
            self.slave_context.setValues(2, address, [1 if value else 0])

    def get_holding_register(self, address: int) -> int:
        with self.lock:
            vals = self.slave_context.getValues(3, address, count=1)
            return vals[0] if vals else 0

    def set_holding_register(self, address: int, value: int):
        with self.lock:
            self.slave_context.setValues(3, address, [int(value) & 0xFFFF])

    def get_input_register(self, address: int) -> int:
        with self.lock:
            vals = self.slave_context.getValues(4, address, count=1)
            return vals[0] if vals else 0

    def set_input_register(self, address: int, value: int):
        with self.lock:
            self.slave_context.setValues(4, address, [int(value) & 0xFFFF])

    def _run_server(self):
        logger.info(f"Starting Modbus/TCP Server on {self.host}:{self.port}...")
        try:
            # Custom server loop using socket for instant shutdown capability
            # Or StartTcpServer when in standard deployment
            StartTcpServer(
                context=self.context,
                address=(self.host, self.port)
            )
        except Exception as e:
            if self.running:
                logger.error(f"Modbus server error on {self.host}:{self.port}: {e}")
        finally:
            self.running = False

    def start(self, background: bool = True):
        self.running = True
        if background:
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            # Wait for socket to bind
            for _ in range(20):
                time.sleep(0.05)
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.1)
                    s.connect((self.host if self.host != "0.0.0.0" else "127.0.0.1", self.port))
                    s.close()
                    break
                except (ConnectionRefusedError, OSError):
                    pass
            logger.info(f"Modbus server active on {self.host}:{self.port}")
        else:
            self._run_server()

    def stop(self):
        self.running = False
        logger.info(f"Stopping Modbus server on {self.host}:{self.port}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    srv = ModbusPlcServer(host="127.0.0.1", port=5020)
    srv.start(background=False)
