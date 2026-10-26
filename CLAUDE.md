# CLAUDE.md

Psittacus is an Anki add-on (Anki 26.9, 64-bit Windows) that replaces Anki's text-to-speech with neural voices: it plays `{{tts}}` tags and saves MP3 audio into note fields. Local engines (Kokoro, Piper) where they're good, Edge TTS for the rest; the model list is data. `README.md` covers use and engines; `docs/DECISIONS.md` records the choices. Psittacus stands on its own: don't assume anki-setup in user-facing text.

## Commands

```sh
local-ci push -u origin <branch>; local-ci wait   # PR checks: ruff format and lint, unit tests
python3 scripts/build.py     # the .ankiaddon (about 200 MB, with the Japanese and Chinese dictionaries)
```

Releases are GitHub Releases of `psittacus-<version>-windows.ankiaddon`, with a CHANGELOG section and a version bump in the same PR. Commit subjects look like `Cap the clip cache at 100 MB; release 0.2.0 (#9)`.

## Seeing it live

Unit tests don't speak. To check behavior in real Anki 26.9.3 on Windows without disturbing the owner's profile: run `Anki.exe -b <throwaway dir>` with `QT_QPA_PLATFORM=offscreen`, seed a `_global` prefs row with `firstRun` false so the first-run dialog doesn't block, and install a small harness add-on that does the check, logs it, and quits. Anki shows any stderr write as an add-on error, so the harness logs stderr too. Never open Anki windows on the owner's desktop without asking.

## Rules

- Engines and voices are data; adding a model shouldn't need new code paths.
- Model downloads go to the add-on's `user_files`; keep the add-on file's size in mind (it's already about 200 MB).
- An engine or voice that fails must degrade to the next option, never break playback.
