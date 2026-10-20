"""The bench's pure parts: job planning, scoring and the report. Engines are not run."""

import json
import sys
import unittest
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent / "bench"
sys.path.insert(0, str(BENCH))

import engines  # noqa: E402
import render  # noqa: E402
import report  # noqa: E402
import score  # noqa: E402

SENTENCES = {
    "en": {"name": "English", "lines": ["cat", "The cat sleeps."]},
    "ja": {"name": "Japanese", "lines": ["猫"]},
}
VOICES = {"a": {"en": {"voice": "A1"}, "ja": {"voice": "A2"}}, "b": {"ja": {"voice": "B1"}}}


class Plan(unittest.TestCase):
    def test_one_job_per_engine_language_and_line(self):
        jobs = render.plan(SENTENCES, VOICES, ["a", "b"], None)
        self.assertEqual(
            [(j["engine"], j["lang"], j["line"], j["voice"]["voice"]) for j in jobs],
            [
                ("a", "en", 0, "A1"),
                ("a", "en", 1, "A1"),
                ("a", "ja", 0, "A2"),
                ("b", "ja", 0, "B1"),
            ],
        )

    def test_language_filter_and_missing_voices(self):
        jobs = render.plan(SENTENCES, VOICES, ["b"], ["en"])
        self.assertEqual(jobs, [])

    def test_unknown_engine_plans_nothing(self):
        self.assertEqual(render.plan(SENTENCES, VOICES, ["zzz"], None), [])


class Score(unittest.TestCase):
    def test_normalize_ignores_case_punctuation_and_spaces(self):
        self.assertEqual(score.normalize("  Hello, World! "), "helloworld")
        self.assertEqual(score.normalize("昨日、駅に傘を。"), "昨日駅に傘を")

    def test_cer(self):
        self.assertEqual(score.cer("Squirrel.", "squirrel"), 0.0)
        self.assertEqual(score.cer("abcd", "abxd"), 0.25)
        self.assertEqual(score.cer("ab", ""), 1.0)
        self.assertEqual(score.cer("ab", "abab"), 1.0)
        self.assertEqual(score.cer("", ""), 0.0)

    def test_resample_keeps_duration_and_shape(self):
        import numpy

        ramp = numpy.linspace(0, 1, 24000, dtype=numpy.float32)  # one second at 24 kHz
        out = score.resample(ramp, 24000)
        self.assertEqual(len(out), 16000)
        self.assertEqual(out.dtype, numpy.float32)
        self.assertAlmostEqual(float(out[-1]), 1.0, places=3)
        self.assertIs(score.resample(out, 16000).dtype, out.dtype)

    def test_whisper_language(self):
        self.assertEqual(score.whisper_language("pt-BR"), "pt")
        self.assertEqual(score.whisper_language("ja"), "ja")


ROWS = [
    {"engine": "a", "lang": "en", "line": 0, "file": "en/a-0.wav", "seconds": 0.5,
     "audio_seconds": 1.0, "heard": "cat", "cer": 0.0},
    {"engine": "a", "lang": "en", "line": 1, "file": "en/a-1.wav", "seconds": 1.0,
     "audio_seconds": 2.0, "heard": "the hat sleeps", "cer": 0.5},
    {"engine": "a", "lang": "ja", "line": 0, "error": "RuntimeError: <boom>"},
]  # fmt: skip


class Report(unittest.TestCase):
    def test_rtf(self):
        self.assertEqual(report.rtf(ROWS[0]), 0.5)
        self.assertIsNone(report.rtf(ROWS[2]))

    def test_summary_counts_only_successful_rows(self):
        self.assertEqual(
            report.summarize("a", ROWS),
            {"languages": 1, "median_cer": 0.25, "median_rtf": 0.5, "median_seconds": 0.75},
        )

    def test_page(self):
        engines_info = [
            {"name": "a", "label": "Engine A", "load_seconds": 2.0, "disk_bytes": 80_000_000},
            {"name": "b", "label": "Engine B", "unavailable": "set B_KEY"},
        ]
        page = report.render(SENTENCES, engines_info, ROWS, "Test box")
        self.assertIn("1 languages · median 0.50× RT · CER 0.25", page)
        self.assertIn("80 MB · load 2.0 s", page)
        self.assertIn("<li>Engine B: set B_KEY</li>", page)
        self.assertIn('<audio controls preload="none" src="en/a-1.wav">', page)
        self.assertIn('<span class="bad">CER 0.50</span>', page)
        self.assertIn('<td class="err">RuntimeError: &lt;boom&gt;</td>', page)
        # A skipped engine gets no column: one header per engine that ran, plus the sentence.
        self.assertEqual(page.count("<th>"), 2)


class Data(unittest.TestCase):
    """The shipped sentences and voice map agree with each other and with the engines."""

    def setUp(self):
        self.sentences = json.loads((BENCH / "sentences.json").read_text(encoding="utf-8"))
        self.voices = json.loads((BENCH / "voices.json").read_text(encoding="utf-8"))

    def test_voice_map_names_real_engines_and_languages(self):
        self.assertEqual(set(self.voices), set(engines.ENGINES))
        for name, langs in self.voices.items():
            with self.subTest(engine=name):
                self.assertLessEqual(set(langs), set(self.sentences))

    def test_every_language_has_a_voice_and_lines(self):
        for lang, info in self.sentences.items():
            with self.subTest(lang=lang):
                self.assertTrue(info["lines"])
                self.assertTrue(any(lang in v for v in self.voices.values()))


if __name__ == "__main__":
    unittest.main()
