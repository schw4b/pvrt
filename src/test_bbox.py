#!/usr/bin/python
"""test_bbox.py Test a TTL parallel button box by Simon Schwab"""
# Copyright (C) 2011 Simon Schwab
# Department of Psychiatric Neurophysiology, University of Bern.
#
# Distributed under the terms of the GNU General Public License (GPL).
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import portio

# init that stuff
status_a = portio.ioperm(0x378, 1, 1)
status_b = portio.ioperm(0x379, 1, 1)
if status_a and status_b:
   print 'ioperm 0x378:', os.strerror(status_a)
   print 'ioperm 0x379:', os.strerror(status_b)
   sys.exit()

portio.outb(0x0, 0x378)

# output the button box to standard out
while True:
   print portio.inb(0x379)
