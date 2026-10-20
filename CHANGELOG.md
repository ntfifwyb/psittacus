# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-20

First version, for Anki 26.9 on 64-bit Windows.

### Added
- `{{tts}}` tags speak with a neural voice: Kokoro for English, Spanish, Brazilian Portuguese, French, Italian and Hindi; Piper for German, Dutch, Polish, Russian, Turkish, Arabic, Japanese and Korean; Edge TTS (online) for the rest, including Chinese. If an engine fails, the next one speaks.
- Clips are cached, so a card speaks instantly from its second play.
- **Browse → Notes → Add Psittacus audio…** saves `[sound:]` MP3 clips into a field of the selected notes, so the audio plays in AnkiDroid and AnkiMobile. Notes whose audio field is already filled are skipped, and the change can be undone.
- Voices per language live in `voices.json`; a `user_files/voices.json` overrides them.

[0.1.0]: https://github.com/ntfifwyb/psittacus/releases/tag/v0.1.0
