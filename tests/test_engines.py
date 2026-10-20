"""Kokoro's phonemizer routing, with a fake model and fake phonemizers. No models."""

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ADDON = Path(__file__).resolve().parent.parent / "addon"
# Load addon/engines.py as part of a bare package, skipping __init__.py, which imports Anki.
package = types.ModuleType("addon")
package.__path__ = [str(ADDON)]
sys.modules.setdefault("addon", package)

from addon import engines  # noqa: E402


class FakeModel:
    def __init__(self):
        self.calls = []

    def create(self, text, voice, lang, speed, is_phonemes):
        self.calls.append((text, voice, lang, speed, is_phonemes))
        return [0.0], 24000


class Token:
    def __init__(self, phonemes, whitespace=""):
        self.phonemes = phonemes
        self.whitespace = whitespace


def kokoro(**g2p):
    k = engines.Kokoro(Path("models"), print)
    k.tts = FakeModel()
    k.g2p = g2p
    return k


@mock.patch.object(engines, "write_mp3")
class Kokoro(unittest.TestCase):
    def test_plain_languages_go_to_kokoro_as_text(self, write_mp3):
        k = kokoro()
        k.synth("Hello", {"voice": "af_heart", "lang": "en-us"}, 1.2, Path("out.mp3"))
        self.assertEqual(k.tts.calls, [("Hello", "af_heart", "en-us", 1.2, False)])
        write_mp3.assert_called_once_with(Path("out.mp3"), [0.0], 24000)

    def test_chinese_goes_to_kokoro_as_misaki_phonemes(self, write_mp3):
        k = kokoro(**{"misaki-zh": lambda text: (f"/{text}/", None)})
        voice = {"voice": "zf_xiaoxiao", "lang": "cmn", "g2p": "misaki-zh"}
        k.synth("你好", voice, 1.0, Path("out.mp3"))
        self.assertEqual(k.tts.calls, [("/你好/", "zf_xiaoxiao", "cmn", 1.0, True)])

    def test_japanese_phonemes_come_from_the_tokens_without_the_pitch_track(self, write_mp3):
        tokens = [Token("koɲɲitɕiβa", " "), Token(None), Token("sekai")]
        k = kokoro(**{"misaki-ja": lambda text: ("koɲɲitɕiβa sekai ˩˥˥", tokens)})
        voice = {"voice": "jf_alpha", "lang": "ja", "g2p": "misaki-ja"}
        k.synth("こんにちは世界", voice, 1.0, Path("out.mp3"))
        self.assertEqual(k.tts.calls[0][0], "koɲɲitɕiβa sekai")

    def test_text_without_phonemes_fails_so_the_next_engine_speaks(self, write_mp3):
        k = kokoro(**{"misaki-ja": lambda text: ("", [])})
        voice = {"voice": "jf_alpha", "lang": "ja", "g2p": "misaki-ja"}
        with self.assertRaisesRegex(RuntimeError, "no phonemes"):
            k.synth("。", voice, 1.0, Path("out.mp3"))
        self.assertEqual(k.tts.calls, [])

    def test_an_unknown_phonemizer_is_an_error_not_unavailable(self, write_mp3):
        k = kokoro()
        with self.assertRaises(ValueError):
            k.synth("x", {"voice": "v", "lang": "xx", "g2p": "nope"}, 1.0, Path("out.mp3"))


if __name__ == "__main__":
    unittest.main()
