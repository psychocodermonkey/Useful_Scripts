#!/usr/bin/env python3

"""
 Program: TermInfo-Export-GhosTTY
    Name: Andrew Dixon            File: TermInfo-Export-GhosTTY.py
    Date: 11 Feb 2026
   Notes: Install Ghostty terminfo on SSH targets.

   Usage:
    python3 TermInfo-Export-GhosTTY.py server system service
    python3 TermInfo-Export-GhosTTY.py server --verify
    python3 TermInfo-Export-GhosTTY.py server.example.com -i ~/.ssh/server_key -p 21234

  Copyright (c) 2026 Andrew Dixon

   This file is part of Useful_Scripts.
   Licensed under the GNU Lesser General Public License v2.1.
   See the LICENSE file at the project root for details.

........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1.........2.........3..
"""

import argparse
from pathlib import Path
import subprocess
import sys


def main(args=None) -> int:
  """Install and verify each target, or only verify when requested.

  Return a nonzero status if any requested operation fails.
  """
  options = parseArgs(args)
  source = None

  # Extract once before connecting so every target receives the same definition.
  if not options.verify:
    source = getSource()

    if source is None:
      return 1

  failed = False

  for target in options.targets:
    if not options.verify:
      print(f'{target}: installing xterm-ghostty...', flush=True)
      result = runRemote(target, options, 'tic -x -', source)

      if result is None:
        failed = True
        continue

      showDiagnostics(target, 'install', result)

      if result.returncode != 0:
        print(f'{target}: installation FAILED (exit {result.returncode})')
        failed = True
        # An existing definition could pass verification despite this failed install.
        continue

      print(f'{target}: installation OK')

    print(f'{target}: verifying xterm-ghostty...', flush=True)
    result = runRemote(target, options, 'infocmp xterm-ghostty', verify=True)

    if result is None:
      failed = True
      continue

    showDiagnostics(target, 'verify', result)

    if result.returncode != 0:
      print(f'{target}: verification FAILED (exit {result.returncode})')
      failed = True

    else:
      print(f'{target}: verification OK')

  return int(failed)


def sshCommand(target: str, options: argparse.Namespace, remoteCommand: str) -> list[str]:
  """Build an OpenSSH command, leaving host and account resolution to SSH."""
  command = ['ssh']

  if options.identity is not None:
    command.extend(['-i', str(options.identity.expanduser())])

  if options.port is not None:
    command.extend(['-p', str(options.port)])

  command.extend([target, remoteCommand])

  return command


def showDiagnostics(target, step, result, showOutput=True) -> None:
  """Display command output and classify stderr using the exit status."""
  if showOutput and result.stdout:
    sys.stdout.buffer.write(result.stdout)
    sys.stdout.flush()

  if result.stderr:
    # tic can emit warnings while still installing successfully.
    label = 'WARNING' if result.returncode == 0 else 'DETAIL'
    print(f'{target}: {step} {label}:', file=sys.stderr)
    sys.stderr.buffer.write(result.stderr)

    if not result.stderr.endswith(b'\n'):
      print(file=sys.stderr)

    sys.stderr.flush()


def getSource() -> bytes | None:
  """Return the local extended terminfo source, or None on failure."""
  try:
    result = subprocess.run(
      ['infocmp', '-x', 'xterm-ghostty'],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      check=False,
    )

  except OSError as error:
    print(f'Local infocmp FAILED: {error}', file=sys.stderr)

    return None

  # The source is passed to SSH later; only diagnostics belong on the console.
  showDiagnostics('local', 'infocmp', result, showOutput=False)

  if result.returncode != 0 or not result.stdout:
    print('Local terminfo extraction FAILED.', file=sys.stderr)

    return None

  return result.stdout


def runRemote(
  target: str,
  options: argparse.Namespace,
  remoteCommand: str,
  source: bytes | None = None,
  verify: bool = False,
) -> subprocess.CompletedProcess[bytes] | None:
  """Run a remote command and return its result, or None if SSH cannot start."""
  try:
    return subprocess.run(
      sshCommand(target, options, remoteCommand),
      input=source,
      # Successful verification needs only the exit status, not the definition.
      stdout=subprocess.DEVNULL if verify else subprocess.PIPE,
      stderr=subprocess.PIPE,
      check=False,
    )

  except OSError as error:
    print(f'{target}: SSH FAILED: {error}', file=sys.stderr)
    return None


def parseArgs(args=None) -> argparse.Namespace:
  """Parse targets and optional SSH overrides from command-line arguments."""
  parser = argparse.ArgumentParser(
    description='Install and verify the local xterm-ghostty terminfo definition over SSH.'
  )

  parser.add_argument('targets', nargs='+', help='SSH aliases or hostnames')
  parser.add_argument('-i', '--identity', type=Path, help='SSH private key file')
  parser.add_argument('-p', '--port', type=int, help='override the SSH port')
  parser.add_argument('--verify', action='store_true', help='check existing installations only')
  parsed = parser.parse_args(args)

  if parsed.port is not None and not 1 <= parsed.port <= 65535:
    parser.error('port must be between 1 and 65535')

  return parsed


# If the TermInfo-Export-GhosTTY.py is run (instead of imported as a module),
#   call the main() function:
if __name__ == '__main__':
  # Return the exit code to the OS.
  raise SystemExit(main())
