#! /usr/local/bin/python3

"""
 Program: Print the path of the environment in a pretty way.
    Name: Andrew Dixon            File: Print-Environment-Path.py
    Date: 11 Nov 2025
   Notes:

   Copyright (c) 2026 Andrew Dixon

   This file is part of Useful_Scripts.
   Licensed under the GNU Lesser General Public License v2.1.
   See the LICENSE file at the project root for details.

........1.........2.........3.........4.........5.........6.........7.........8.........9.........0.........1
"""

import os

print(os.environ['PATH'].replace(':','\n'))
