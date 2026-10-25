#!/usr/bin/env python3

"""
 Program: Wake PC from LAN
    Name: Andrew Dixon            File: Wake-on-LAN.py
    Date: 11 Nov 2025
   Notes:

  Copyright (c) 2026 Andrew Dixon

  This file is part of Useful_Scripts.
  Licensed under the GNU Lesser General Public License v2.1.
  See the LICENSE file at the project root for details.
........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1
"""

from typing import LiteralString

import socket
import struct
import shutil
import sys
import time

BROADCAST = '0.0.0.255'         # Update to the broadcast IP address of your network.
SYSTEM = 'de:ad:be:ef:90:4c'    # Update to the MAC address of the machine you need to start.
FQDN = 'system.example.com'     # Update to the FQDN or system name. Set to None if none.


SSH_PORT = 22                   # Set to SSH port in use for verification of host coming active.
SSH_WAIT_TIMEOUT = 60           # Set to a time in seconds longer than the host normally takes to boot.
SSH_RETRY_INTERVAL = 2          # How often to ping the SSH port for a connection.
PROGRESS_REFRESH_INTERVAL = 0.1 # How often do you want the progress bar to update.
ORANGE = '\033[38;5;208m'       # Set the color to orange for the progress bar.
RESET = '\033[0m'               # Reset terminal code to reset the terminal.


def main() -> None:
  mac_address: LiteralString = SYSTEM.replace(SYSTEM[2], '')
  data: LiteralString = ''.join(['FFFFFFFFFFFF', mac_address * 20])
  send_data = b''

  print(f'Unencoded packet data:\n{data}\n\nEncoding packet data .....\n')

  for i in range(0, len(data), 2):
    send_data: bytes = b''.join([send_data, struct.pack('B', int(data[i : i + 2], 16))])

  print(f'Encoded packet data:\n{send_data}\n')

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  sock.sendto(send_data, (BROADCAST, 7))

  print(f'\nWoL packet sent to {SYSTEM} ({FQDN}).\n')

  if FQDN:
    wait_for_ssh(FQDN)


def show_progress(start: float, deadline: float) -> None:
  """Draw the SSH wait progress bar using the current terminal width."""

  columns: int = shutil.get_terminal_size(fallback=(80, 24)).columns
  bar_width: int = max(10, columns - 7)
  elapsed: float = time.monotonic() - start
  progress: float = min(1, max(0, elapsed / (deadline - start)))
  filled: int = int(bar_width * progress)
  percent: int = int(progress * 100)
  filled_bar: str = '█' * filled
  empty_bar: str = ' ' * (bar_width - filled)
  color: str = ORANGE if sys.stdout.isatty() else ''
  reset: str = RESET if color else ''

  print(f'\r[{color}{filled_bar}{reset}{empty_bar}] {percent:3d}%', end='', flush=True)


def wait_for_ssh(hostname) -> bool:
  """Wait for an SSH server banner without authenticating."""

  start: float = time.monotonic()
  deadline: float = start + SSH_WAIT_TIMEOUT
  print(f'Waiting up to {SSH_WAIT_TIMEOUT}s for SSH on {hostname}...')
  show_progress(start, deadline)

  while time.monotonic() < deadline:
    try:
      ip_address: str = socket.gethostbyname(hostname)

      with socket.create_connection((ip_address, SSH_PORT), timeout=1) as sock:
        banner: bytes = sock.recv(255)

      if banner.startswith(b'SSH-'):
        print()
        print(f'SSH is available on {hostname} ({ip_address}).\n')
        return True

    except socket.gaierror, socket.timeout, OSError:
      pass

    remaining: float = deadline - time.monotonic()

    if remaining > 0:
      wait_until: float = time.monotonic() + min(SSH_RETRY_INTERVAL, remaining)
      while time.monotonic() < wait_until:
        show_progress(start, deadline)
        time.sleep(max(0, min(PROGRESS_REFRESH_INTERVAL, wait_until - time.monotonic())))

  show_progress(start, deadline)
  print()
  print(f'Timed out: SSH not become available on {hostname}.\n')
  return False


def interact():
  ''' Using python -i Wake-on-LAN.py it will execute globals and drop into REPL '''
  import code
  code.InteractiveConsole(locals=globals()).interact()


# If the ${FILE} is run (instead of imported as a module), call the main() function:
if __name__ == '__main__':
  # Register the function to execute on ending the script
  main()
