"""The candidate engines. Each one loads its model on demand and writes one audio file per call.

Engine libraries are imported inside load(), so the rest of the bench (and its tests) runs
without them installed.
"""

from __future__ import annotations

import asyncio
import base64
import os
import subprocess
from pathlib import Path

KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


class Unavailable(Exception):
    """The engine can't run here: a missing key, model, or dependency. The message says which."""


def dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


class Engine:
    name = ""
    label = ""
    local = True
    ext = ".wav"

    def __init__(self, cache: Path):
        self.cache = cache / self.name

    def load(self, voices: list[dict]) -> None:
        """Download and initialize what synth() needs for these voices."""

    def synth(self, text: str, voice: dict, out: Path) -> None:
        raise NotImplementedError

    def disk_bytes(self) -> int | None:
        """Size of the downloaded model files, or None for cloud engines."""
        return dir_size(self.cache) if self.local and self.cache.exists() else None


class Kokoro(Engine):
    name = "kokoro"
    label = "Kokoro 82M (ONNX, fp32)"
    model = "kokoro-v1.0.onnx"

    def load(self, voices):
        import urllib.request

        from kokoro_onnx import Kokoro as Model

        self.cache.mkdir(parents=True, exist_ok=True)
        for name in (self.model, "voices-v1.0.bin"):
            if not (self.cache / name).exists():
                urllib.request.urlretrieve(KOKORO_URL + name, self.cache / name)
        self.tts = Model(str(self.cache / self.model), str(self.cache / "voices-v1.0.bin"))
        # espeak reads kanji as "Chinese letter", so Japanese and Chinese go through misaki,
        # the phonemizer Kokoro was trained with.
        self.g2p = {}
        kinds = {v.get("g2p") for v in voices}
        if "misaki-ja" in kinds:
            from misaki import ja

            self.g2p["misaki-ja"] = ja.JAG2P(version="pyopenjtalk")
        if "misaki-zh" in kinds:
            from misaki import zh

            self.g2p["misaki-zh"] = zh.ZHG2P()

    def disk_bytes(self):
        return sum((self.cache / n).stat().st_size for n in (self.model, "voices-v1.0.bin"))

    def phonemes(self, text: str, kind: str) -> str:
        result, tokens = self.g2p[kind](text)
        if tokens is None:
            return result
        # JAG2P's string carries a pitch track after the phonemes; rebuild from the tokens.
        return "".join((t.phonemes or "") + t.whitespace for t in tokens)

    def synth(self, text, voice, out):
        import soundfile

        kind = voice.get("g2p")
        if kind:
            text = self.phonemes(text, kind)
        audio, rate = self.tts.create(
            text, voice=voice["voice"], lang=voice["lang"], is_phonemes=bool(kind)
        )
        soundfile.write(out, audio, rate)


class Piper(Engine):
    name = "piper"
    label = "Piper (ONNX, one model per voice)"

    def load(self, voices):
        from piper import PiperVoice
        from piper.download_voices import download_voice

        self.cache.mkdir(parents=True, exist_ok=True)
        self.models = {}
        for v in voices:
            name = v["voice"]
            if not (self.cache / f"{name}.onnx").exists():
                download_voice(name, self.cache)
            self.models[name] = PiperVoice.load(self.cache / f"{name}.onnx")

    def disk_bytes(self):
        # Every voice is its own model; report one so the column compares like with like.
        sizes = [p.stat().st_size for p in self.cache.glob("*.onnx")]
        return max(sizes) if sizes else None

    def synth(self, text, voice, out):
        import numpy
        import soundfile

        # Collect the chunks first: synthesize_wav hides a phonemizer error behind a wave error.
        chunks = list(self.models[voice["voice"]].synthesize(text))
        if not chunks:
            raise RuntimeError("no audio")
        audio = numpy.concatenate([c.audio_float_array for c in chunks])
        soundfile.write(out, audio, chunks[0].sample_rate)


class Moss(Engine):
    """MOSS-TTS-Nano 100M through its own ONNX CLI, in a checkout and venv the user sets up.

    Its runtime needs PyTorch and WeTextProcessing, so it runs out of process. Each call
    reloads the model, so its timings include model load.
    """

    name = "moss"
    label = "MOSS-TTS-Nano 100M (ONNX, per call incl. load)"

    def load(self, voices):
        repo = os.environ.get("PSITTACUS_MOSS_DIR")
        if not repo:
            raise Unavailable(
                "set PSITTACUS_MOSS_DIR to a MOSS-TTS-Nano checkout (see bench/README)"
            )
        self.repo = Path(repo)
        venv = self.repo / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        self.python = os.environ.get("PSITTACUS_MOSS_PYTHON", str(venv / "python"))
        if not Path(self.python).exists():
            raise Unavailable(f"no Python at {self.python}; set PSITTACUS_MOSS_PYTHON")

    def disk_bytes(self):
        models = self.repo / "models"
        return dir_size(models) if models.exists() else None

    def synth(self, text, voice, out):
        cmd = [self.python, "infer_onnx.py", "--text", text, "--voice", voice["voice"]]
        cmd += ["--output-audio-path", str(out)]
        done = subprocess.run(cmd, cwd=self.repo, capture_output=True, text=True)
        if done.returncode:
            raise RuntimeError(done.stderr.strip().splitlines()[-1] if done.stderr else "failed")


class Edge(Engine):
    name = "edge"
    label = "Edge TTS (Microsoft, unofficial, free)"
    local = False
    ext = ".mp3"

    def load(self, voices):
        import edge_tts

        self.edge_tts = edge_tts

    def synth(self, text, voice, out):
        asyncio.run(self.edge_tts.Communicate(text, voice["voice"]).save(str(out)))


class Gemini(Engine):
    name = "gemini"
    label = "Gemini 3.8 Flash TTS (free tier)"
    local = False
    model = "gemini-3.8-flash-tts"

    def load(self, voices):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise Unavailable("set GEMINI_API_KEY (free from Google AI Studio)")
        from google import genai

        self.client = genai.Client(api_key=key)

    def synth(self, text, voice, out):
        reply = self.client.interactions.create(
            model=self.model,
            input=[{"type": "user_input", "content": [{"type": "text", "text": text}]}],
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice["voice"]}]},
        )
        out.write_bytes(base64.b64decode(reply.output_audio.data))


ENGINES = {e.name: e for e in (Kokoro, Moss, Piper, Edge, Gemini)}
