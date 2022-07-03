#!/usr/bin/env python3

"""
  includes code ported from zlib:
  crc32.c -- compute the CRC-32 of a data stream
  Copyright (C) 1995-2011 Jean-loup Gailly and Mark Adler
  This software is provided 'as-is', without any express or implied
  warranty.  In no event will the authors be held liable for any damages
  arising from the use of this software.
  Permission is granted to anyone to use this software for any purpose,
  including commercial applications, and to alter it and redistribute it
  freely, subject to the following restrictions:
  1. The origin of this software must not be misrepresented; you must not
     claim that you wrote the original software. If you use this software
     in a product, an acknowledgment in the product documentation would be
     appreciated but is not required.
  2. Altered source versions must be plainly marked as such, and must not be
     misrepresented as being the original software.
  3. This notice may not be removed or altered from any source distribution.
  Jean-loup Gailly        Mark Adler
  jloup@gzip.org          madler@alumni.caltech.edu
"""

# https://github.com/toomuchio/pycrc32combine

def gf2_matrix_square(square, mat):
  for n in range(0, 32):
    square[n] = gf2_matrix_times(mat, mat[n])
  return square

def gf2_matrix_times(mat, vec):
  sum = 0
  i = 0
  while vec:
    if (vec & 1):
      sum = sum ^ mat[i]
    vec = (vec >> 1) & 0x7FFFFFFF
    i = i + 1
  return sum

crc32_reversed_poly = 0xedb88320
crc32_reciprocal_poly = 0xdb710641

def crc32_combine(crc1, crc2, len2):
  """
  https://stackoverflow.com/a/23126768
  crc32(crc32(0, seq1, len1), seq2, len2) ==
    crc32_combine(crc32(0, seq1, len1), crc32(0, seq2, len2), len2)
  """
  even = [0] * 32
  odd = []
  if (len2 == 0): # degenerate case
    return crc1

  odd.append(crc32_reversed_poly)
  row = 1

  for _ in range(1, 32):
    odd.append(row)
    row = row << 1

  even = gf2_matrix_square(even, odd)
  odd = gf2_matrix_square(odd, even)

  while (len2 != 0):
    even = gf2_matrix_square(even, odd)
    if (len2 & 1):
      crc1 = gf2_matrix_times(even, crc1)
    len2 = len2 >> 1

    if (len2 == 0):
      break

    odd = gf2_matrix_square(odd, even)
    if (len2 & 1):
      crc1 = gf2_matrix_times(odd, crc1)
    len2 = len2 >> 1

  crc1 = crc1 ^ crc2
  return crc1

def crc32_subtract(crc1, crc2, len2):
  """
  https://stackoverflow.com/a/59139701
  """
  even = [0] * 32
  odd = []
  if (len2 == 0): # degenerate case
    return crc1

  for n in range(1, 32):
    odd.append(1 << n)

  odd.append(crc32_reciprocal_poly)

  even = gf2_matrix_square(even, odd)
  odd = gf2_matrix_square(odd, even)

  crc1 ^= crc2

  while (len2 != 0):
    even = gf2_matrix_square(even, odd)
    if (len2 & 1):
      crc1 = gf2_matrix_times(even, crc1)
    len2 = len2 >> 1

    if (len2 == 0):
      break

    odd = gf2_matrix_square(odd, even)
    if (len2 & 1):
      crc1 = gf2_matrix_times(odd, crc1)
    len2 = len2 >> 1

  return crc1


def make_crc32_table():
    """
    https://github.com/madler/zlib/blob/21767c654d31d2dccdde4330529775c6c5fd5389/crc32.c#L273
    """
    table = [0] * 256

    for byte in range(256):
        crc = byte
        for bit in range(8):
            if (crc & 1):
                crc = (crc >> 1) ^ crc32_reversed_poly
            else:
                crc >>= 1
        table[byte] = crc

    return table

crc32_table = make_crc32_table()

def crc32_compute_checksum(crc, bytes):
    for b in bytes:
        crc = (crc >> 8) ^ crc32_table[(crc ^ b) & 0xff]
    return crc
