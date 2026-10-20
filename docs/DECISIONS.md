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
