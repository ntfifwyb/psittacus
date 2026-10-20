"""Language routing, engine fallback and the audio cache.

No Anki imports, so it runs and is tested outside Anki. The engines live in engines.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Protocol


class Unavailable(Exception):
    """The engine can't run here (missing package, failed download). Skipped until restart."""


class NoVoice(Exception):
    """No engine could speak the text. The message lists what each one said."""


class Engine(Protocol):
    def synth(self, text: str, voice: dict, speed: float, out: Path) -> None:
        """Write MP3 audio to out, raising Unavailable if the engine can't run at all."""


def load_voices(*paths: Path) -> dict:
    """Read the voice data file; a later file's engines and languages override earlier ones."""
    data: dict = {"order": [], "voices": {}}
    for path in paths:
        if not path.exists():
            continue
        extra = json.loads(path.read_text(encoding="utf-8"))
        data["order"] = extra.get("order", data["order"])
        for engine, table in extra.get("voices", {}).items():
            data["voices"].setdefault(engine, {}).update(table)
    return data


def lang_keys(lang: str) -> list[str]:
    """Data-file keys to try for an Anki language code, most specific first.

    >>> lang_keys("pt_BR")
    ['pt-BR', 'pt']
    """
    base, _, region = lang.replace("_", "-").partition("-")
    base = base.lower()
    return [f"{base}-{region.upper()}", base] if region else [base]


def candidates(lang: str, data: dict) -> list[tuple[str, dict]]:
    """(engine, voice) pairs for a language, in the data file's engine order."""
    found = []
    for engine in data["order"]:
        table = data["voices"].get(engine, {})
        key = next((k for k in lang_keys(lang) if k in table), None)
        if key:
            found.append((engine, table[key]))
    return found


def languages(data: dict) -> list[str]:
    """Every language some engine in the order can speak, as Anki codes (pt_BR)."""
    keys = {k for e in data["order"] for k in data["voices"].get(e, {})}
    return sorted(k.replace("-", "_") for k in keys)


def cache_name(engine: str, voice: dict, text: str, speed: float) -> str:
    key = json.dumps([engine, voice, text, speed], sort_keys=True, ensure_ascii=False)
    return f"psittacus-{hashlib.sha1(key.encode()).hexdigest()[:20]}.mp3"


class Speaker:
    """Speaks text with the first engine that can, caching each clip by engine, voice and text."""

    def __init__(self, engines: dict[str, Engine], data: dict, cache: Path):
        self.engines = engines
        self.data = data
        self.cache = cache
        self.broken: dict[str, str] = {}
        # One synthesis at a time: models are large, and Anki may ask from several threads.
        self.lock = threading.Lock()

    def speak(self, text: str, lang: str, speed: float = 1.0) -> Path:
        text = " ".join(text.split())
        if not text:
            raise NoVoice("nothing to say")
        errors = []
        for name, voice in candidates(lang, self.data):
            engine = self.engines.get(name)
            if engine is None:
                continue
            if name in self.broken:
                errors.append(f"{name}: {self.broken[name]}")
                continue
            path = self.cache / cache_name(name, voice, text, speed)
            if path.exists():
                return path
            part = path.with_suffix(".part")
            try:
                with self.lock:
                    self.cache.mkdir(parents=True, exist_ok=True)
                    engine.synth(text, voice, speed, part)
                os.replace(part, path)
                return path
            except Unavailable as e:
                self.broken[name] = str(e)
                errors.append(f"{name}: {e}")
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
            finally:
                part.unlink(missing_ok=True)
        if not errors:
            raise NoVoice(f"no voice for {lang}")
        raise NoVoice("; ".join(errors))
