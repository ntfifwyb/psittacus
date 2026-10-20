"""Psittacus: neural text-to-speech for Anki.

Plays {{tts}} tags with the routed engine, and saves [sound:] clips into note fields from
the Browse screen so they reach the phone apps, which don't run add-ons.
"""

from __future__ import annotations

import site
from pathlib import Path

HERE = Path(__file__).resolve().parent
USER = HERE / "user_files"  # kept by Anki when the add-on updates
# The engines' packages, built for Anki's Python. Appended, so Anki's own copies win.
site.addsitedir(str(HERE / "vendor"))

from aqt import gui_hooks, mw  # noqa: E402
from aqt.operations import CollectionOp, QueryOp  # noqa: E402
from aqt.qt import (  # noqa: E402
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
)
from aqt.sound import av_player  # noqa: E402
from aqt.tts import TTSProcessPlayer, TTSVoice, TTSVoiceMatch  # noqa: E402
from aqt.utils import tooltip  # noqa: E402

from . import core  # noqa: E402
from .engines import ENGINES  # noqa: E402

VOICE = "Psittacus"
_speaker: core.Speaker | None = None


def notify(message: str) -> None:
    mw.taskman.run_on_main(lambda: tooltip(f"Psittacus: {message}", period=8000))


def speaker() -> core.Speaker:
    global _speaker
    if _speaker is None:
        data = core.load_voices(HERE / "voices.json", USER / "voices.json")
        engines = {name: cls(USER / "models", notify) for name, cls in ENGINES.items()}
        _speaker = core.Speaker(engines, data, USER / "cache")
    return _speaker


# {{tts}} playback
##########################################################################


class Player(TTSProcessPlayer):
    def get_available_voices(self):
        return [TTSVoice(name=VOICE, lang=lang) for lang in core.languages(speaker().data)]

    def voice_for_tag(self, tag):
        if not core.candidates(tag.lang, speaker().data):
            return None
        # Psittacus speaks every tag of a language it covers, unless the tag asks for
        # another voice that exists (Anki gives a requested voice rank 0, a fallback -100).
        if VOICE in tag.voices:
            rank = -tag.voices.index(VOICE)
        elif tag.voices:
            rank = -60
        else:
            rank = -10
        return TTSVoiceMatch(voice=TTSVoice(name=VOICE, lang=tag.lang), rank=rank)

    def _play(self, tag):
        self._taskman.run_on_main(lambda: gui_hooks.av_player_did_begin_playing(self, tag))
        return speaker().speak(core.clean_text(tag.field_text), tag.lang, tag.speed)

    def _on_done(self, ret, cb):
        if error := ret.exception():
            tooltip(f"Psittacus: {error}")
            cb()
            return
        if self._terminate_flag:  # the card changed while the clip was being made
            cb()
            return
        av_player.current_player = None
        av_player.insert_file(str(ret.result()))


def register_player() -> None:
    # Anki rebuilds its player list each time a profile opens.
    if not any(isinstance(p, Player) for p in av_player.players):
        av_player.players.append(Player(mw.taskman))


gui_hooks.profile_did_open.append(register_player)


# Saving audio into notes
##########################################################################


class FillDialog(QDialog):
    """Pick the text field, the audio field and the language."""

    def __init__(self, parent, fields: list[str], langs: list[str], config: dict):
        super().__init__(parent)
        self.setWindowTitle("Add Psittacus audio")
        self.source, self.target, self.lang = QComboBox(), QComboBox(), QComboBox()
        self.source.addItems(fields)
        self.target.addItems(fields)
        self.lang.addItems(langs)
        self.source.currentTextChanged.connect(self.guess_target)
        for box, key in ((self.source, "source"), (self.lang, "language")):
            if config.get(key) in [box.itemText(i) for i in range(box.count())]:
                box.setCurrentText(config[key])
        self.guess_target(self.source.currentText())
        if config.get("target") in fields and config.get("source") == self.source.currentText():
            self.target.setCurrentText(config["target"])
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout(self)
        form.addRow("Read the text in", self.source)
        form.addRow("Save the audio in", self.target)
        form.addRow("Language", self.lang)
        form.addRow(QLabel("Notes whose audio field is already filled are skipped."))
        form.addRow(buttons)

    def guess_target(self, source: str) -> None:
        if self.target.findText(source + "Audio") >= 0:
            self.target.setCurrentText(source + "Audio")

    def choice(self) -> dict:
        return {
            "source": self.source.currentText(),
            "target": self.target.currentText(),
            "language": self.lang.currentText(),
        }


def fill_selected(browser) -> None:
    nids = browser.selected_notes()
    if not nids:
        tooltip("Select the notes to add audio to first.")
        return
    notes = [mw.col.get_note(nid) for nid in nids]
    fields = list(dict.fromkeys(name for note in notes for name in note.keys()))
    config = mw.addonManager.getConfig(__name__) or {}
    dialog = FillDialog(browser, fields, core.languages(speaker().data), config)
    if not dialog.exec():
        return
    choice = dialog.choice()
    mw.addonManager.writeConfig(__name__, choice)
    if choice["source"] == choice["target"]:
        tooltip("Pick two different fields.")
        return
    fill_notes(browser, nids, choice)


def fill_notes(parent, nids, choice: dict, done=None) -> None:
    """Speak each note's source field into its empty target field, then report.

    The clips are made in the background without the collection, then saved as one
    undoable change. done, if given, receives the report too.
    """
    col = mw.col
    notes = [col.get_note(nid) for nid in nids]
    source, target = choice["source"], choice["target"]
    jobs = core.fill_jobs(
        [
            (n.id, n[source] if source in n else None, n[target] if target in n else None)
            for n in notes
        ]
    )
    skipped = len(notes) - len(jobs)

    def synthesize(_col):
        clips, errors, stopped = [], [], False
        for i, (nid, text) in enumerate(jobs):
            if mw.progress.want_cancel():
                stopped = True
                break
            label = f"Speaking {i + 1} of {len(jobs)}: {text[:40]}"
            mw.taskman.run_on_main(
                lambda label=label, i=i: mw.progress.update(label=label, value=i, max=len(jobs))
            )
            try:
                clips.append((nid, speaker().speak(text, choice["language"])))
            except core.NoVoice as e:
                errors.append(str(e))
        return clips, errors, stopped

    def save(result):
        clips, errors, stopped = result
        changed = []
        for nid, path in clips:
            note = col.get_note(nid)
            if note[target].strip():  # filled while we were speaking
                continue
            note[target] = f"[sound:{col.media.add_file(str(path))}]"
            changed.append(note)

        def update(col):
            return col.update_notes(changed)

        def finished(_changes):
            message = core.fill_report(len(changed), skipped, errors, stopped)
            tooltip(message, parent=parent, period=8000)
            if done:
                done(message)

        CollectionOp(parent=parent, op=update).success(finished).run_in_background()

    QueryOp(parent=parent, op=synthesize, success=save).without_collection().with_progress(
        "Psittacus is speaking…"
    ).run_in_background()


def add_browser_action(browser) -> None:
    action = browser.form.menu_Notes.addAction("Add Psittacus audio…")
    action.triggered.connect(lambda: fill_selected(browser))


gui_hooks.browser_menus_did_init.append(add_browser_action)
