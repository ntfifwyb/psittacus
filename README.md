# Psittacus

An Anki add-on that replaces Anki's text-to-speech with modern neural voices. *Psittacus* is Latin for parrot.

It's for cards you write yourself and for decks that come without audio: select the notes, and Psittacus speaks them with a voice much closer to a person than your system's text-to-speech.

- **Plays `{{tts}}` tags.** Existing templates such as `{{tts en_US:Front}}` speak with a neural voice on desktop, with no change to your cards. Audio is generated on first play and cached.
- **Saves audio into notes.** Writes `[sound:...]` MP3 files into a field, so the audio syncs to AnkiDroid and AnkiMobile, which don't run add-ons.
- **Picks the best voice per language.** Local models (free, offline, no limits) are used where they're good, and free cloud voices cover the rest. The model list is data, so new models can be added without rewriting the add-on.

## Install

Psittacus runs on Anki 26.9 for 64-bit Windows. Download `psittacus-<version>-windows.ankiaddon` from the [latest release](https://github.com/ntfifwyb/psittacus/releases/latest) and double-click it, or use **Tools → Add-ons → Install from file…**, then restart Anki. The file is about 200 MB, most of it Japanese and Chinese dictionaries, so these languages work offline.

The first clip in a language downloads that engine's model once, into the add-on's `user_files` folder: 340 MB for Kokoro, 60–110 MB per Piper voice. Edge TTS needs no download but needs the internet every time it speaks.

## Use

**Playing tags.** Psittacus speaks every `{{tts}}` tag in a language it covers. A tag that names another voice that exists, such as `{{tts en_US voices=Microsoft_Zira:Front}}`, keeps that voice; `voices=Psittacus` asks for Psittacus explicitly. `{{tts-voices:}}` lists the languages.

**Saving audio into notes.** In **Browse**, select the notes, then **Notes → Add Psittacus audio…**. Pick the field to read (say `Example`), the empty field to save into (`ExampleAudio`), and the language. HTML is stripped before speaking. Notes whose audio field already holds anything are skipped, so you can run it again after adding notes, or after stopping it partway. **Edit → Undo** removes the audio from the fields; the files stay in the media folder until **Tools → Check Media**.

Then put the audio field in the card template, for example `{{ExampleAudio}}`, and sync.

## Languages and engines

| Engine | Runs | Languages |
|---|---|---|
| Kokoro 82M | on your computer | English (US, UK), Spanish, Portuguese (BR), French, Italian, Hindi, Japanese, Chinese |
| Piper | on your computer | German, Dutch, Polish, Russian, Turkish, Arabic, Korean |
| Edge TTS | Microsoft's servers, unofficial | Chinese, Portuguese (PT), and the above if a local engine fails |

Each language goes to the first engine with a voice for it. If that engine fails, the next one speaks; an engine that can't run at all (a failed download, say) is skipped until Anki restarts. The order and voices are in `voices.json`. To change them, copy it to `user_files/voices.json` and edit the copy: its entries override the shipped ones and survive updates.

## Develop

- `.local-ci` runs the checks: ruff format and lint, and the unit tests.
- `uv run --no-project scripts/build.py` builds `dist/psittacus-<version>-windows.ankiaddon`, with the engines' packages resolved for Anki's Python 3.13 on Windows (it runs from WSL too).
- [`bench/`](bench/README.md) is the listening test that chose the engines: it renders the same sentences in 15 languages with each candidate, times them, and checks with Whisper that each clip says the right words.

Psittacus's engines also work outside Anki, for decks that make their audio when they're built (as [ntfifwyb/anki-setup](https://github.com/ntfifwyb/anki-setup) does): `addon/core.py` and `addon/engines.py` don't import Anki, and `core.Speaker` names each clip as the add-on does, so a deck's clips and the add-on's never duplicate.

Decisions are logged in [docs/DECISIONS.md](docs/DECISIONS.md).

## License

MIT. The built `.ankiaddon` also bundles other packages under their own licenses, in `vendor/`: notably Piper and eSpeak NG (GPL-3.0) and onnxruntime (MIT).
