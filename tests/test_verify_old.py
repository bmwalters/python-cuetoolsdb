#!/usr/bin/env python3

from pathlib import Path
import unittest

from cuetoolsdb import verify_old
from cuetoolsdb.cdda import Track, SAMPLES_PER_FRAME

def offsets_to_toc(offsets: list[int]):
    """
    :param offsets: a list of track start frames followed by the end frame
    :returns: a toc of tracks with length next_track_start - current_track_end.
    """
    return list(map(
        lambda pair: Track(start=pair[0], length=pair[1] - pair[0]),
        zip(offsets, offsets[1:])
    ))


class VerifyTestCase(unittest.TestCase):
    def test_compute_track_crc_no_offset(self):
        tracks = offsets_to_toc([13, 68, 99, 136])

        toc = verify_old.TOCForVerifyOld(
            Pregap=tracks[0].start,
            Leadout=tracks[-1].start + tracks[-1].length,
            AudioTracks=3,
            AudioLength=tracks[0].start + sum([track.length for track in tracks]),
            FirstAudio=1,
            TrackLengths=[track.length for track in tracks],
            TrackStarts=[track.start for track in tracks],
            TrackPregaps=[tracks[0].start, 0, 0]
        )

        BYTES_PER_SAMPLE = 4
        samples = (Path(__file__).parent / "fixtures/test-case.bin").read_bytes()
        self.assertEqual(toc.AudioLength * SAMPLES_PER_FRAME * BYTES_PER_SAMPLE, len(samples))

        written = verify_old.write(toc, samples)

        self.assertEqual(4209773141, verify_old.CTDBCRC_track(toc, written, 1, 0, 5 * 588, 5 * 588))
        self.assertEqual(  37001035, verify_old.CTDBCRC_track(toc, written, 2, 0, 5 * 588, 5 * 588))
        self.assertEqual(1024656428, verify_old.CTDBCRC_track(toc, written, 3, 0, 5 * 588, 5 * 588))
