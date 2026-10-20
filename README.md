# Psittacus

An Anki add-on that replaces Anki's text-to-speech with modern neural voices. *Psittacus* is Latin for parrot.

Planned behavior:

- **Plays `{{tts}}` tags.** Existing templates such as `{{tts en_US:Front}}` speak with a neural voice on desktop, with no change to your cards. Audio is generated on first play and cached.
- **Saves audio into notes.** Writes `[sound:...]` files into a field, so the audio syncs to AnkiDroid and AnkiMobile, which don't run add-ons.
- **Picks the best voice per language.** Local models (free, offline, no limits) are used where they're good, and free cloud voices cover the rest. The model list is data, so new models can be added without rewriting the add-on.

Status: choosing models. The listening test in `bench/` renders the same flashcard sentences with each candidate engine so they can be compared by ear before the add-on is built.

Decisions are logged in [docs/DECISIONS.md](docs/DECISIONS.md).
