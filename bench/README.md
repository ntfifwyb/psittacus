# Listening test

Renders the same flashcard sentences (`sentences.json`: a lone word and a short sentence in 15 languages) with every candidate engine and writes `bench-out/index.html`: a row per sentence, a column per engine, with a player, the synthesis time, and what Whisper heard.

```sh
uv run bench/render.py                        # everything
uv run bench/render.py -e kokoro edge -l ja   # some engines and languages
uv run bench/render.py --no-asr               # skip the Whisper check
```

The first run downloads the models (about 0.4 GB for Kokoro, 60–110 MB per Piper voice, 0.5 GB for Whisper small) into `~/.cache/psittacus-bench`.

## What the numbers mean

- **Time** is one call for one sentence, after a warm-up call. For Anki, this is the wait before a card speaks the first time.
- **RT** (real-time factor) is synthesis time over audio length; below 1 is faster than playback.
- **CER** is the character error rate of a Whisper transcript against the sentence. It catches a voice saying the wrong words, not one that sounds flat. Whisper has its own spelling habits (kana for kanji, traditional for simplified Chinese), so compare engines on the same row rather than across rows. Above 0.3 is flagged red.

## Engines

| Engine | Runs | Languages here | Setup |
|---|---|---|---|
| Kokoro 82M | local, onnxruntime | 8 | none |
| Piper | local, onnxruntime | 14 (no Chinese: its phonemizer needs PyTorch) | none |
| Edge TTS | Microsoft's servers, unofficial | 15 | none |
| Gemini 3.8 Flash TTS | Google's servers | 15 | `GEMINI_API_KEY` |
| MOSS-TTS-Nano 100M | local, its own CLI | 13 | checkout, below |

Voices per language are in `voices.json`. Kokoro's Japanese and Chinese go through `misaki`, the phonemizer Kokoro was trained with: its default espeak path reads every kanji as "Chinese letter".

### Gemini

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey), then `GEMINI_API_KEY=... uv run bench/render.py -e gemini`. The free tier has a small daily quota and Google may use free-tier requests to improve its products; the bench sends only the sentences in `sentences.json`.

### MOSS-TTS-Nano

Its runtime needs PyTorch and WeTextProcessing, so it runs from its own checkout and venv, once per sentence (its times include model load). Setup, following its README:

```sh
git clone https://github.com/OpenMOSS/MOSS-TTS-Nano.git
cd MOSS-TTS-Nano
uv venv -p 3.12
uv pip install pynini==2.1.6.post1 && uv pip install -r requirements.txt
cd -
PSITTACUS_MOSS_DIR=/path/to/MOSS-TTS-Nano uv run bench/render.py -e moss
```

It downloads its ONNX models into the checkout's `models/` on first use. Its built-in voices are Chinese, English and Japanese; other languages use the English voice "Ava", so expect an accent.
