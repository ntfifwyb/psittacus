# Decisions

Dated log of product choices. Check here before asking a question again.

## 2026-10-20: Name
Psittacus (Latin for parrot), repo `ntfifwyb/psittacus`. Chosen by the user over Lector and Otto.

## 2026-10-20: Both playback modes
Psittacus plays `{{tts}}` tags on desktop through Anki's TTS player registry, and can also save `[sound:]` files into notes so audio reaches the mobile apps. Chosen by the user.

## 2026-10-20: State-of-the-art small models, broad language coverage
The user wants the smallest, most effective current models, and many languages without giving up quality. Models change weekly, so engines and voices live in a data file and Psittacus routes each language to the best available engine. A generic OpenAI-compatible endpoint lets users plug in large GPU models (Breeze TTS 2, Fish Audio, OmniVoice) that can't ship inside Anki.

## 2026-10-20: Listening test before the add-on
The first step is `bench/`: render the same sentences with Kokoro, Piper, MOSS-TTS-Nano, Edge TTS and Gemini TTS, measure speed, and let the user pick engines by ear. Chosen by the user.

## 2026-10-20: Target platform
The user runs Anki 26.9.3 on Windows desktop (Python 3.13). The add-on runs in Anki's bundled Python, so PyTorch-based models can't ship inside it; local engines must run on onnxruntime.

## 2026-10-20: Kokoro's Japanese and Chinese go through misaki (decided by Claude, pending review)
kokoro-onnx phonemizes with espeak by default, which reads every kanji as "Chinese letter". The bench uses misaki (pyopenjtalk backend for Japanese), the phonemizer Kokoro was trained with. The add-on will need the same, which means shipping pyopenjtalk's native wheel per platform.

## 2026-10-20: Whisper intelligibility check in the bench (decided by Claude, pending review)
Claude can't listen, and leaderboards don't cover every language. The bench transcribes each clip with Whisper small and reports the character error rate against the sentence, which catches voices saying the wrong words. Listening still decides naturalness.

## 2026-10-20: No Piper voice for Chinese (decided by Claude, pending review)
Piper's Chinese phonemizer (g2pW) needs PyTorch, which can't ship in Anki.

## 2026-10-20: MOSS-TTS-Nano runs only when the user sets it up (decided by Claude, pending review)
Its runtime needs PyTorch, torchaudio and WeTextProcessing even on the ONNX path, and it isn't on PyPI, so the bench calls a checkout the user installs. Its core decode loop is numpy and onnxruntime only, and its built-in voices are pre-encoded, so a PyTorch-free port for the add-on looks possible.

## 2026-10-20: Engines per language
After listening to the bench, the user liked Kokoro and Piper most and found all three (Kokoro, Piper, Edge) good enough. Each language goes to the first engine in this order that has a voice for it, and falls back to the next one if that engine is missing or fails:

1. **Kokoro**: English, Spanish, Portuguese (BR), French, Italian, Hindi, Japanese, Chinese
2. **Piper**: German, Dutch, Polish, Russian, Turkish, Arabic, Korean, and any other language it has a voice for
3. **Edge TTS** (online): every language neither local engine covers

Gemini and MOSS-TTS-Nano weren't heard and stay out of the default order until they are.

## 2026-10-20: First target deck is English Expressions, with audio saved into notes
The user reviews on the phone too, so the English Expressions deck (`ntfifwyb/anki-setup`, `decks/english-expressions/build.py`) gets `ExpressionAudio` and `ExampleAudio` fields, and its templates play `[sound:]` files instead of `{{tts}}` tags. The Produce front stays silent, since audio would give the answer away. The Produce back plays the whole example sentence. The Recognise front plays the expression, and its back plays the example. Psittacus's save-to-note mode therefore maps a source field to a target audio field (Expression → ExpressionAudio, Example → ExampleAudio), strips HTML, and skips notes whose target field is already filled.

## 2026-10-20: Kokoro's full-precision model
The add-on downloads Kokoro's fp32 model (310 MB, plus 27 MB of voices) on first use: the one heard in the bench. The int8 model (88 MB) wasn't heard. Chosen by the user.

## 2026-10-20: Kokoro's Japanese and Chinese come later
v0.1 doesn't bundle misaki and pyopenjtalk, so Japanese goes to Piper and Chinese to Edge TTS until a later version adds them. The English deck doesn't need them, and the add-on stays smaller. Chosen by the user.

## 2026-10-20: Clips are MP3 (decided by Claude, pending review)
Every engine's output is saved as MP3 (soundfile encodes it; Edge already sends MP3): small enough to sync, and played by AnkiDroid and AnkiMobile.
