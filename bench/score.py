"""Intelligibility check: transcribe each clip with Whisper and compare it with its text.

A rough, objective signal next to listening: it catches a voice reading the wrong words (espeak
saying "Chinese letter" for every kanji) but not a flat or unnatural one. Whisper has its own
spelling habits (kana for kanji, traditional for simplified), so compare engines on the same
sentence rather than reading the numbers as absolute.
"""

from __future__ import annotations

import unicodedata

WHISPER_MODEL = "small"


def normalize(text: str) -> str:
    """Casefold and drop everything but letters, marks and digits, so only the words count."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(c for c in text if unicodedata.category(c)[0] in "LMN")


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate: edit distance over the reference length, after normalizing both."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        current = [i]
        for j, h in enumerate(hyp, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (r != h)))
        previous = current
    return previous[-1] / len(ref)


def whisper_language(lang: str) -> str:
    """Whisper's code for a sentences.json key: "pt-BR" -> "pt"."""
    return lang.split("-")[0]


def resample(audio, rate: int, target: int = 16000):
    """Linear resampling of a mono float array: plenty for speech recognition."""
    import numpy

    if rate == target:
        return audio.astype(numpy.float32)
    count = round(len(audio) * target / rate)
    positions = numpy.arange(count) * (rate / target)
    return numpy.interp(positions, numpy.arange(len(audio)), audio).astype(numpy.float32)


def load_16k(path: str):
    """Whisper's input: 16 kHz mono float32. Decoded with soundfile, not faster-whisper's PyAV."""
    import soundfile

    audio, rate = soundfile.read(path, dtype="float32", always_2d=True)
    return resample(audio.mean(axis=1), rate)


class Transcriber:
    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    def __call__(self, path: str, lang: str) -> str:
        segments, _ = self.model.transcribe(
            load_16k(path), language=whisper_language(lang), beam_size=5
        )
        return "".join(s.text for s in segments).strip()
