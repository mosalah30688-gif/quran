"""اختبار سرعة التلاوة: المدة تتغيّر وطبقة الصوت تبقى.

تُقاس الطبقة بعدّ مرات عبور الصفر في موجة جيبية ٤٤٠ هرتز: لو تغيّرت الطبقة
لَتَغيّر التردد المقاس بنفس نسبة السرعة.
"""
import array
import math
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from PySide6.QtWidgets import QApplication  # noqa: E402

import main as M  # noqa: E402

APP = QApplication.instance() or QApplication(sys.argv)
TONE_HZ = 440.0


def write_tone(path, seconds=3.0):
    rate = M.AudioEngine.RATE
    frames = array.array('h')
    for index in range(int(seconds * rate)):
        value = int(12000 * math.sin(2 * math.pi * TONE_HZ * index / rate))
        frames.append(value)
        frames.append(value)
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames.tobytes())


def drive(engine, writes=400):
    audio = bytearray()
    for _ in range(writes):
        if engine.gen is None:
            break
        data = engine.gen.send(engine.CHUNK)
        audio.extend(data if isinstance(data, bytes) else b'')
        if engine.ended:
            break
    return bytes(audio)


class PlaybackRateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tone = Path(cls.tmp.name) / 'tone.wav'
        write_tone(cls.tone)
        cls.ma = M._miniaudio()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def engine(self, rate):
        engine = M.AudioEngine()
        engine.allow_null = True
        engine.set_rate(rate)
        engine.src = self.ma.stream_file(
            str(self.tone), output_format=self.ma.SampleFormat.SIGNED16,
            nchannels=2, sample_rate=engine.RATE, frames_to_read=engine.CHUNK,
        )
        next(engine.src)
        engine.gen = engine._callback()
        next(engine.gen)
        return engine

    def measure(self, audio):
        samples = array.array('h', audio)
        mono = samples[0::2]
        seconds = len(mono) / M.AudioEngine.RATE
        crossings = sum(1 for left, right in zip(mono, mono[1:]) if (left < 0) != (right < 0))
        frequency = crossings/2/seconds if seconds else 0.0
        return seconds, frequency

    def test_rate_is_clamped(self):
        engine = M.AudioEngine()
        engine.set_rate(9)
        self.assertEqual(engine.rate, 2.0)
        engine.set_rate(0.1)
        self.assertEqual(engine.rate, 0.5)

    def test_faster_shortens_duration(self):
        normal_seconds, _ = self.measure(drive(self.engine(1.0)))
        fast_seconds, _ = self.measure(drive(self.engine(1.5)))
        slow_seconds, _ = self.measure(drive(self.engine(0.75)))
        self.assertGreater(fast_seconds, 0)
        self.assertLess(fast_seconds, normal_seconds * 0.92)
        self.assertGreater(slow_seconds, normal_seconds * 1.08)

    def test_pitch_is_preserved(self):
        for rate in (0.75, 1.25, 1.5):
            _seconds, frequency = self.measure(drive(self.engine(rate)))
            self.assertAlmostEqual(frequency, TONE_HZ, delta=TONE_HZ * 0.12,
                                   msg=f'طبقة الصوت تغيّرت عند السرعة {rate}')

    def test_output_is_never_clipped_silence(self):
        audio = drive(self.engine(1.25))
        samples = array.array('h', audio)
        self.assertGreater(max(abs(value) for value in samples), 1000)


if __name__ == '__main__':
    unittest.main()
