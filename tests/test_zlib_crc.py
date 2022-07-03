#!/usr/bin/env python3

import unittest

from cuetoolsdb import zlib_crc

class ZlibCRCTestCase(unittest.TestCase):
    testBytes = [0, 0, 1, 0, 254, 255, 253, 255, 255, 127, 254, 127, 3, 128, 4, 128]

    def test_combine(self):
        lenAB = len(self.testBytes)
        lenA = 7
        lenB = lenAB - lenA

        crcAB = zlib_crc.crc32_compute_checksum(0, bytes(self.testBytes))
        crcA = zlib_crc.crc32_compute_checksum(0, bytes(self.testBytes[:lenA]))
        crcB = zlib_crc.crc32_compute_checksum(0, bytes(self.testBytes[lenA:]))

        self.assertEqual(crcAB, zlib_crc.crc32_combine(crcA, crcB, lenB), "CRC32 was not combined correctly.")
        self.assertEqual(crcB, zlib_crc.crc32_combine(crcA, crcAB, lenB), "CRC32 was not combined correctly.")

        self.assertEqual(crcA, zlib_crc.crc32_subtract(crcAB, crcB, lenB), "CRC32 was not subtracted correctly.")

    def test_compute_checksum(self):
        actual = zlib_crc.crc32_compute_checksum(0xffffffff, self.testBytes) ^ 0xffffffff
        self.assertEqual(2028688632, actual, "CRC32 was not computed correctly.")
