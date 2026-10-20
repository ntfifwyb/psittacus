"""Turn bench results into one HTML page: a row per sentence, a column per engine."""

from __future__ import annotations

from html import escape
from pathlib import Path
from statistics import median

# Above this character error rate Whisper heard clearly different words: worth a listen.
BAD_CER = 0.3

NOTE = (
    "Times are per sentence, after one warm-up call per engine. RT is the real-time factor "
    "(synthesis time over audio length; below 1 is faster than playback). Cloud times include "
    "the network; load times on a first run include downloads. CER is the character error rate "
    "of a Whisper transcript against the sentence (0 is exact)."
)
STYLE = (Path(__file__).parent / "report.css").read_text(encoding="utf-8")


def rtf(row: dict) -> float | None:
    """Real-time factor: synthesis time over audio length. Below 1 is faster than playback."""
    if row.get("error") or not row.get("audio_seconds"):
        return None
    return row["seconds"] / row["audio_seconds"]


def summarize(engine: str, rows: list[dict]) -> dict:
    ok = [r for r in rows if r["engine"] == engine and not r.get("error")]
    factors = [f for f in map(rtf, ok) if f is not None]
    errors = [r["cer"] for r in ok if "cer" in r]
    return {
        "languages": len({r["lang"] for r in ok}),
        "median_cer": median(errors) if errors else None,
        "median_rtf": median(factors) if factors else None,
        "median_seconds": median(r["seconds"] for r in ok) if ok else None,
    }


def megabytes(n: int | None) -> str:
    return "cloud" if n is None else f"{n / 1e6:.0f} MB"


def cell(row: dict | None) -> str:
    if row is None:
        return '<td class="m">no voice</td>'
    if row.get("error"):
        return f'<td class="err">{escape(row["error"])}</td>'
    factor = rtf(row)
    speed = f" · {factor:.2f}× RT" if factor is not None else ""
    heard = ""
    if "cer" in row:
        flag = ' class="bad"' if row["cer"] > BAD_CER else ""
        heard = (
            f'<div class="m" title="Whisper heard: {escape(row["heard"])}">'
            f"<span{flag}>CER {row['cer']:.2f}</span> · {escape(row['heard'])}</div>"
        )
    return (
        f'<td><audio controls preload="none" src="{escape(row["file"])}"></audio>'
        f'<div class="m">{row["seconds"]:.2f} s{speed}</div>{heard}</td>'
    )


def render(sentences: dict, engines: list[dict], rows: list[dict], machine: str) -> str:
    by_key = {(r["engine"], r["lang"], r["line"]): r for r in rows}
    ran = [e for e in engines if not e.get("unavailable")]
    skipped = "".join(
        f"<li>{escape(e['label'])}: {escape(e['unavailable'])}</li>"
        for e in engines
        if e not in ran
    )
    head = ["<th>Sentence</th>"]
    for e in ran:
        s = summarize(e["name"], rows)
        factor = "n/a" if s["median_rtf"] is None else f"{s['median_rtf']:.2f}× RT"
        cer = "" if s["median_cer"] is None else f" · CER {s['median_cer']:.2f}"
        detail = (
            f"{s['languages']} languages · median {factor}{cer}<br>"
            f"{megabytes(e.get('disk_bytes'))} · load {e.get('load_seconds', 0):.1f} s"
        )
        head.append(f'<th>{escape(e["label"])}<div class="note">{detail}</div></th>')
    body = []
    for lang, info in sentences.items():
        for i, text in enumerate(info["lines"]):
            label = f'<span class="lang">{escape(info["name"])}</span><br>' if i == 0 else ""
            cells = "".join(cell(by_key.get((e["name"], lang, i))) for e in ran)
            body.append(f"<tr><td>{label}{escape(text)}</td>{cells}</tr>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Psittacus listening test</title><style>{STYLE}</style></head><body>"
        "<h1>Psittacus listening test</h1>"
        f'<p class="note">Rendered on {escape(machine)}. {NOTE}</p>'
        + (f'<p class="note">Skipped:</p><ul class="note">{skipped}</ul>' if skipped else "")
        + f'<div class="wrap"><table><thead><tr>{"".join(head)}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
        "</body></html>"
    )
