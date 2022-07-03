#!/usr/bin/env python3

"""
Includes code ported from upstream CUETools:
Copyright (C) 2006-2008  Moitah (moitah@yahoo.com)
Copyright (C) 2008-2022  Gregory S. Chudov (gchudov@gmail.com)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from dataclasses import dataclass

from cuetoolsdb.zlib_crc import crc32_combine, crc32_table

SAMPLES_PER_FRAME = 588

@dataclass(frozen=True, kw_only=True)
class TOCForVerifyOld:
    Pregap: int
    """length of the pregap in frames"""
    Leadout: int
    """length of the leadout in frames"""
    AudioTracks: int
    """number of audio tracks (consecutive, in the middle) of the disc"""
    AudioLength: int
    """length of audio section in frames"""
    FirstAudio: int
    """1-based index of first audio track."""
    TrackLengths: list[int]
    """mapping from 0-based track number to track length in frames"""
    TrackStarts: list[int]
    """mapping from 0-based track number to track start time in frames"""
    TrackPregaps: list[int]
    """mapping from 0-based track number to track pregap length in frames"""

def Array_Copy(src: list[int], srci: int, dst: list[int], dsti: int, length: int):
    for i in range(length):
        dst[dsti + i] = src[srci + i]

def write(toc: TOCForVerifyOld, sampleBuffer: bytes) -> list[list[int]]:
    """
    Given audio data, returns CRC data for each track.
    Each track has multiple CRCs computed with varying offsets
    """

    pos = 0

    _sampleCount = 0

    _currentTrack = 0
    _samplesRemTrack = 0
    _samplesDoneTrack = 0

    tempLocation = 0
    for iTrack in range(toc.AudioTracks + 1):
        tempLen = (toc.TrackPregaps[toc.FirstAudio - 1] if iTrack == 0 else toc.TrackLengths[toc.FirstAudio + iTrack - 2]) * SAMPLES_PER_FRAME
        if (tempLocation + tempLen) > _sampleCount:
            _currentTrack = iTrack
            _samplesRemTrack = tempLocation + tempLen - _sampleCount
            _samplesDoneTrack = _sampleCount - tempLocation
            break
        tempLocation += tempLen

    maxOffset = 4096 * 2
    if maxOffset % SAMPLES_PER_FRAME != 0:
        maxOffset += SAMPLES_PER_FRAME - maxOffset % SAMPLES_PER_FRAME

    _CRC32 = [[0 for _ in range(3 * maxOffset)] for _ in range(toc.AudioTracks + 1)]

    while pos < len(sampleBuffer):
        # Process no more than there is in the buffer, no more than there is in this track, and no more than up to a sector boundary.
        copyCount = min(min(len(sampleBuffer) - pos, _samplesRemTrack), SAMPLES_PER_FRAME - _sampleCount % SAMPLES_PER_FRAME)

        offset = -1
        if _samplesDoneTrack < maxOffset:
            offset = _samplesDoneTrack
        elif _samplesRemTrack <= maxOffset:
            offset = 2 * maxOffset - _samplesRemTrack
        elif _samplesDoneTrack >= 445 * SAMPLES_PER_FRAME and _samplesDoneTrack <= 455 * SAMPLES_PER_FRAME:
            offset = 2 * maxOffset + 1 + _samplesDoneTrack - 445 * SAMPLES_PER_FRAME

        crcTrack = (_currentTrack - 1) if _samplesDoneTrack == 0 and _currentTrack > 0 else _currentTrack
        crc32 = _CRC32[crcTrack][2 * maxOffset]

        for i in range(copyCount):
            if offset >= 0:
                _CRC32[_currentTrack][offset + i] = crc32

            sampleIndex = pos + i
            sample = int.from_bytes(sampleBuffer[sampleIndex * 4:(sampleIndex + 1) * 4], byteorder="little")

            lo = sample & 0xffff
            crc32 = (crc32 >> 8) ^ crc32_table[(crc32 ^ lo) & 0xff]
            crc32 = (crc32 >> 8) ^ crc32_table[(crc32 ^ (lo >> 8)) & 0xff]

            hi = sample >> 16
            crc32 = (crc32 >> 8) ^ crc32_table[(crc32 ^ hi) & 0xff]
            crc32 = (crc32 >> 8) ^ crc32_table[(crc32 ^ (hi >> 8)) & 0xff]

        _CRC32[_currentTrack][2 * maxOffset] = crc32

        # duplicate prefix to suffix
        if _samplesDoneTrack < maxOffset and _samplesRemTrack <= maxOffset:
            Array_Copy(_CRC32[_currentTrack], _samplesDoneTrack,
                _CRC32[_currentTrack], 2 * maxOffset - _samplesRemTrack,
                copyCount)

        # duplicate prefix to pregap
        if _sampleCount < maxOffset and _currentTrack == 1:
            Array_Copy(_CRC32[_currentTrack], _samplesDoneTrack,
                _CRC32[0], _sampleCount,
                copyCount)

        pos += copyCount
        _samplesRemTrack -= copyCount
        _samplesDoneTrack += copyCount
        _sampleCount += copyCount

        while _samplesRemTrack <= 0:
            _currentTrack += 1
            if _currentTrack > toc.AudioTracks:
                return _CRC32
            _samplesRemTrack = toc.TrackLengths[_currentTrack + toc.FirstAudio - 2] * SAMPLES_PER_FRAME
            _samplesDoneTrack = 0

    assert False, "buffer data was not sufficient to populate all track crcs"

def CTDBCRC_track(toc: TOCForVerifyOld, CRC32: list[list[int]], iTrack: int, offset: int, prefixSamples: int, suffixSamples: int) -> int:
    maxOffset = 4096 * 2
    if maxOffset % SAMPLES_PER_FRAME != 0:
        maxOffset += SAMPLES_PER_FRAME - maxOffset % SAMPLES_PER_FRAME

    prefixSamples += offset
    suffixSamples -= offset
    if prefixSamples < 0 or prefixSamples >= maxOffset or suffixSamples < 0 or suffixSamples > maxOffset:
        raise ValueError("argument out of range")

    posA = toc.TrackStarts[iTrack + toc.FirstAudio - 2] * SAMPLES_PER_FRAME + (offset if iTrack > 1 else prefixSamples)
    posB = toc.TrackStarts[iTrack + 1 + toc.FirstAudio - 2] * SAMPLES_PER_FRAME + offset if iTrack < toc.AudioTracks else toc.Leadout * SAMPLES_PER_FRAME - suffixSamples

    if offset > 0:
        crcA = CRC32[iTrack][offset] if iTrack > 1 else CRC32[iTrack][prefixSamples]
        crcB = CRC32[iTrack + 1][offset] if iTrack < toc.AudioTracks else CRC32[iTrack][maxOffset * 2 - suffixSamples]
    else:
        crcA = CRC32[iTrack - 1][maxOffset * 2 + offset] if iTrack > 1 else CRC32[iTrack][prefixSamples]
        crcB = CRC32[iTrack][maxOffset * 2 + offset] if iTrack < toc.AudioTracks else CRC32[iTrack][maxOffset * 2 - suffixSamples]

    # Use 0xffffffff as an initial state
    return 0xffffffff ^ crc32_combine(0xffffffff ^ crcA, crcB, (posB - posA) * 4)

def CTDBCRC_disc(toc: TOCForVerifyOld, CRC32: list[list[int]], offset: int):
    maxOffset = 4096 * 2
    if maxOffset % SAMPLES_PER_FRAME != 0:
        maxOffset += SAMPLES_PER_FRAME - maxOffset % SAMPLES_PER_FRAME

    finalSampleCount = toc.AudioLength * SAMPLES_PER_FRAME

    stride = 10 * SAMPLES_PER_FRAME * 2
    laststride = stride + ((finalSampleCount - toc.Pregap) * 2) % stride

    prefixSamples = stride // 2
    suffixSamples = laststride // 2

    prefixSamples += offset
    suffixSamples -= offset
    if prefixSamples < 0 or prefixSamples >= maxOffset or suffixSamples < 0 or suffixSamples > maxOffset:
        raise ValueError("argument out of range")

    discLen = (toc.AudioLength - toc.Pregap) * SAMPLES_PER_FRAME
    chunkLen = discLen - prefixSamples - suffixSamples
    return 0xffffffff ^ crc32_combine(
        0xffffffff ^ CRC32[1][prefixSamples],
        CRC32[toc.AudioTracks][2 * maxOffset - suffixSamples],
        chunkLen * 4
    )
