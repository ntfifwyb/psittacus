"""The engines Psittacus routes between. Each downloads its model files on first use.

Engine packages are imported on first use too, so a missing one only makes that engine
Unavailable, and the rest of the add-on (and its tests) loads without them.
"""

from __future__ import annotations

import asyncio
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .core import Unavailable

KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
PIPER_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"

Notify = Callable[[str], None]


def download(url: str, path: Path) -> None:
    """Fetch url to path through a .part file, so an interrupted download is never used."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, open(part, "wb") as f:
            while chunk := response.read(1 << 20):
                f.write(chunk)
        os.replace(part, path)
    except OSError as e:
        raise Unavailable(f"couldn't download {url}: {e}") from e
    finally:
        part.unlink(missing_ok=True)


def write_mp3(out: Path, audio, rate: int) -> None:
    import soundfile

    soundfile.write(out, audio, rate, format="MP3")


class Kokoro:
    files = {"kokoro-v1.0.onnx": "310 MB", "voices-v1.0.bin": "27 MB"}

    def __init__(self, models: Path, notify: Notify):
        self.dir = models / "kokoro"
        self.notify = notify
        self.tts = None

    def load(self):
        for name, size in self.files.items():
            if not (self.dir / name).exists():
                self.notify(f"Downloading the Kokoro voice model ({size}), once…")
                download(KOKORO_URL + name, self.dir / name)
        try:
            from kokoro_onnx import Kokoro as Model
        except ImportError as e:
            raise Unavailable(f"kokoro_onnx isn't installed: {e}") from e
        try:
            self.tts = Model(*(str(self.dir / name) for name in self.files))
        except Exception as e:
            raise Unavailable(f"couldn't load Kokoro: {e}") from e

    def synth(self, text, voice, speed, out):
        if self.tts is None:
            self.load()
        audio, rate = self.tts.create(text, voice=voice["voice"], lang=voice["lang"], speed=speed)
        write_mp3(out, audio, rate)


class Piper:
    def __init__(self, models: Path, notify: Notify):
        self.dir = models / "piper"
        self.notify = notify
        self.voices = {}

    def load(self, name: str):
        try:
            from piper import PiperVoice
        except ImportError as e:
            raise Unavailable(f"piper isn't installed: {e}") from e
        model = self.dir / f"{name}.onnx"
        if not model.exists():
            self.notify(f"Downloading the Piper voice {name} (60–110 MB), once…")
            # en_US-lessac-high lives at en/en_US/lessac/high/.
            lang, speaker, quality = name.split("-")
            url = f"{PIPER_URL}{lang.split('_')[0]}/{lang}/{speaker}/{quality}/{name}.onnx"
            download(url + ".json", model.with_suffix(".onnx.json"))
            download(url, model)
        try:
            self.voices[name] = PiperVoice.load(model)
        except Exception as e:
            raise Unavailable(f"couldn't load Piper voice {name}: {e}") from e

    def synth(self, text, voice, speed, out):
        import numpy
        from piper import SynthesisConfig

        name = voice["voice"]
        if name not in self.voices:
            self.load(name)
        config = SynthesisConfig(length_scale=1 / speed)
        chunks = list(self.voices[name].synthesize(text, config))
        if not chunks:
            raise RuntimeError("no audio")
        audio = numpy.concatenate([c.audio_float_array for c in chunks])
        write_mp3(out, audio, chunks[0].sample_rate)


class Edge:
    """Microsoft Edge's online voices, through the unofficial edge-tts client."""

    def __init__(self, models: Path, notify: Notify):
        pass

    def synth(self, text, voice, speed, out):
        try:
            import edge_tts
        except ImportError as e:
            raise Unavailable(f"edge_tts isn't installed: {e}") from e
        rate = f"{round((speed - 1) * 100):+d}%"
        asyncio.run(edge_tts.Communicate(text, voice["voice"], rate=rate).save(str(out)))


ENGINES = {"kokoro": Kokoro, "piper": Piper, "edge": Edge}
