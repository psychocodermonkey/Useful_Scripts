#!/usr/bin/env python3

"""
  Program: Wake PC from LAN
     Name: Andrew Dixon            File: Wake-on-LAN.py
     Date: 11 Nov 2025
    Notes:

 ........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1
"""

import socket
import struct

BROADCAST = '0.0.0.255'         # Update to the broadcast IP address of your network.
SYSTEM = 'de:ad:be:ef:90:4c'    # Update to the MAC address of the machine you need to start.


def main():
  mac_address = SYSTEM.replace(SYSTEM[2], '')
  data = ''.join(['FFFFFFFFFFFF', mac_address * 20])
  send_data = b''

  print(f'Unencoded packet data:\n{data}\n\nEncoding packet data .....\n')

  for i in range(0, len(data), 2):
    send_data = b''.join([send_data, struct.pack('B', int(data[i: i + 2], 16))])

  print(f'Encoded packet data:\n{send_data}\n')

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  sock.sendto(send_data, (BROADCAST, 7))

  print(f'\nWoL packet sent to system ({SYSTEM}).\n')


def interact():
  ''' Using python -i wakeMoxie.py it will execute globals and drop into REPL '''
  import code
  code.InteractiveConsole(locals=globals()).interact()


# If the ${FILE} is run (instead of imported as a module), call the main() function:
if __name__ == '__main__':
  # Register the function to execute on ending the script
  main()
