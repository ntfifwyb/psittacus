"""The add-on's routing, fallback and cache, with fake engines. No Anki, no models."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The add-on package imports Anki; core.py alone doesn't, so import it as a module.
sys.path.insert(0, str(ROOT / "addon"))

import core  # noqa: E402

DATA = {
    "order": ["a", "b", "c"],
    "voices": {
        "a": {"en": {"voice": "A-en"}, "en-GB": {"voice": "A-gb"}},
        "b": {"en": {"voice": "B-en"}, "de": {"voice": "B-de"}},
        "c": {"ja": {"voice": "C-ja"}},
        "unlisted": {"ko": {"voice": "U-ko"}},
    },
}


class Fake:
    def __init__(self, fail=None):
        self.fail = fail
        self.calls = []

    def synth(self, text, voice, speed, out):
        self.calls.append((text, voice["voice"], speed))
        if self.fail:
            raise self.fail
        out.write_bytes(f"{voice['voice']}:{text}".encode())


class Routing(unittest.TestCase):
    def test_lang_keys(self):
        self.assertEqual(core.lang_keys("en_US"), ["en-US", "en"])
        self.assertEqual(core.lang_keys("pt-br"), ["pt-BR", "pt"])
        self.assertEqual(core.lang_keys("JA"), ["ja"])

    def test_candidates_follow_the_order_and_prefer_the_region(self):
        self.assertEqual(
            core.candidates("en_GB", DATA), [("a", {"voice": "A-gb"}), ("b", {"voice": "B-en"})]
        )
        self.assertEqual(
            core.candidates("en_US", DATA), [("a", {"voice": "A-en"}), ("b", {"voice": "B-en"})]
        )

    def test_engines_outside_the_order_are_ignored(self):
        self.assertEqual(core.candidates("ko_KR", DATA), [])
        self.assertEqual(core.languages(DATA), ["de", "en", "en_GB", "ja"])

    def test_shipped_voices_route_english_to_kokoro(self):
        data = core.load_voices(ROOT / "addon" / "voices.json")
        self.assertEqual(data["order"], ["kokoro", "piper", "edge"])
        self.assertEqual(
            [e for e, _ in core.candidates("en_US", data)], ["kokoro", "piper", "edge"]
        )
        self.assertEqual([e for e, _ in core.candidates("zh_CN", data)], ["edge"])

    def test_a_user_file_overrides_single_voices(self):
        with tempfile.TemporaryDirectory() as d:
            base, user = Path(d, "base.json"), Path(d, "user.json")
            base.write_text(json.dumps(DATA))
            user.write_text(json.dumps({"voices": {"a": {"en": {"voice": "Mine"}}}}))
            data = core.load_voices(base, user, Path(d, "missing.json"))
        self.assertEqual(data["order"], ["a", "b", "c"])
        self.assertEqual(data["voices"]["a"], {"en": {"voice": "Mine"}, "en-GB": {"voice": "A-gb"}})


class Speaking(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name, "cache")

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_engine_speaks_and_the_clip_is_cached(self):
        a, b = Fake(), Fake()
        speaker = core.Speaker({"a": a, "b": b}, DATA, self.cache)
        path = speaker.speak("  Hello\n there ", "en_US")
        self.assertEqual(path.read_bytes(), b"A-en:Hello there")
        self.assertEqual(speaker.speak("Hello there", "en_US"), path)
        self.assertEqual(a.calls, [("Hello there", "A-en", 1.0)])
        self.assertEqual(b.calls, [])
        self.assertEqual([p.suffix for p in self.cache.iterdir()], [".mp3"])

    def test_speed_is_part_of_the_cache_key(self):
        a = Fake()
        speaker = core.Speaker({"a": a}, DATA, self.cache)
        self.assertNotEqual(speaker.speak("Hi", "en", 1.0), speaker.speak("Hi", "en", 1.5))

    def test_a_failure_falls_back_and_is_retried_next_time(self):
        a, b = Fake(fail=RuntimeError("boom")), Fake()
        speaker = core.Speaker({"a": a, "b": b}, DATA, self.cache)
        self.assertEqual(speaker.speak("Hi", "en").read_bytes(), b"B-en:Hi")
        speaker.speak("Bye", "en")
        self.assertEqual(len(a.calls), 2)
        self.assertEqual(list(self.cache.glob("*.part")), [])

    def test_an_unavailable_engine_is_skipped_until_restart(self):
        a, b = Fake(fail=core.Unavailable("no model")), Fake()
        speaker = core.Speaker({"a": a, "b": b}, DATA, self.cache)
        speaker.speak("Hi", "en")
        speaker.speak("Bye", "en")
        self.assertEqual(len(a.calls), 1)
        self.assertEqual(len(b.calls), 2)
        self.assertEqual(speaker.broken, {"a": "no model"})

    def test_engines_that_are_not_installed_are_skipped(self):
        b = Fake()
        speaker = core.Speaker({"b": b}, DATA, self.cache)
        self.assertEqual(speaker.speak("Hallo", "de_DE").read_bytes(), b"B-de:Hallo")

    def test_errors_name_every_engine_tried(self):
        a, b = Fake(fail=core.Unavailable("no model")), Fake(fail=RuntimeError("offline"))
        speaker = core.Speaker({"a": a, "b": b}, DATA, self.cache)
        with self.assertRaises(core.NoVoice) as e:
            speaker.speak("Hi", "en")
        self.assertEqual(str(e.exception), "a: no model; b: RuntimeError: offline")
        with self.assertRaises(core.NoVoice) as e:
            speaker.speak("Hi again", "en")
        self.assertEqual(str(e.exception), "a: no model; b: RuntimeError: offline")

    def test_nothing_to_say_or_no_voice(self):
        speaker = core.Speaker({"a": Fake()}, DATA, self.cache)
        with self.assertRaisesRegex(core.NoVoice, "nothing to say"):
            speaker.speak(" \n", "en")
        with self.assertRaisesRegex(core.NoVoice, "no voice for ko_KR"):
            speaker.speak("annyeong", "ko_KR")


if __name__ == "__main__":
    unittest.main()
