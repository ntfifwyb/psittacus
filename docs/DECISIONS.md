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
