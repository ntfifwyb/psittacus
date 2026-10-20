# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = [
#   "kokoro-onnx==0.6.1",
#   "piper-tts[ja]==1.8.0",
#   "misaki==0.9.4",
#   "pyopenjtalk-plus==0.4.1.post9",
#   "jieba==0.42.1",
#   "pypinyin==0.55.0",
#   "cn2an==0.5.24",
#   "ordered-set==4.1.0",
#   "edge-tts==7.3.1",
#   "faster-whisper==1.2.1",
#   "google-genai==2.31.0",
#   "soundfile==0.13.1",
# ]
# ///
"""Render every sentence with every engine and write an HTML page to compare them by ear.

uv run bench/render.py                       # all engines, all languages
uv run bench/render.py -e kokoro edge -l ja  # a subset
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import engines as eng
import report
import score

HERE = Path(__file__).parent


def plan(sentences: dict, voices: dict, names: list[str], langs: list[str] | None) -> list[dict]:
    """One job per (engine, language, line) that the engine has a voice for."""
    jobs = []
    for name in names:
        for lang, info in sentences.items():
            voice = voices.get(name, {}).get(lang)
            if voice is None or (langs and lang not in langs):
                continue
            for i, text in enumerate(info["lines"]):
                jobs.append({"engine": name, "lang": lang, "line": i, "text": text, "voice": voice})
    return jobs


def audio_seconds(path: Path) -> float:
    import soundfile

    return soundfile.info(str(path)).duration


def run_engine(engine: eng.Engine, jobs: list[dict], out: Path) -> tuple[dict, list[dict]]:
    info = {"name": engine.name, "label": engine.label}
    start = time.perf_counter()
    try:
        engine.load([j["voice"] for j in jobs])
    except Exception as e:  # a missing key or a broken dependency skips just this engine
        reason = str(e) if isinstance(e, eng.Unavailable) else f"{type(e).__name__}: {e}"
        print(f"  {engine.name}: skipped, {reason}")
        return {**info, "unavailable": reason}, []
    info["load_seconds"] = time.perf_counter() - start
    info["disk_bytes"] = engine.disk_bytes()

    rows = []
    warm = out / f"warmup-{engine.name}{engine.ext}"
    for job in jobs:
        rel = f"{job['lang']}/{engine.name}-{job['line']}{engine.ext}"
        row = {k: job[k] for k in ("engine", "lang", "line")}
        try:
            if not warm.exists():
                engine.synth(job["text"], job["voice"], warm)
            (out / job["lang"]).mkdir(exist_ok=True)
            start = time.perf_counter()
            engine.synth(job["text"], job["voice"], out / rel)
            row |= {"seconds": time.perf_counter() - start, "file": rel}
            row["audio_seconds"] = audio_seconds(out / rel)
        except Exception as e:  # one bad voice shouldn't stop the rest of the run
            row["error"] = f"{type(e).__name__}: {e}"[:300]
        print(f"  {engine.name} {job['lang']} {job['line']}: {row.get('error') or 'ok'}")
        rows.append(row)
    warm.unlink(missing_ok=True)
    return info, rows


def check(rows: list[dict], sentences: dict, out: Path) -> None:
    """Transcribe every clip and store what Whisper heard and its character error rate."""
    print(f"whisper {score.WHISPER_MODEL}:")
    transcribe = score.Transcriber()
    for row in rows:
        if row.get("error"):
            continue
        text = sentences[row["lang"]]["lines"][row["line"]]
        try:
            row["heard"] = transcribe(str(out / row["file"]), row["lang"])
        except Exception as e:  # one unreadable clip shouldn't lose the rest of the scores
            print(f"  {row['engine']} {row['lang']} {row['line']}: {type(e).__name__}: {e}")
            continue
        row["cer"] = score.cer(text, row["heard"])
        print(f"  {row['engine']} {row['lang']} {row['line']}: {row['cer']:.2f} {row['heard']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument(
        "-e", "--engines", nargs="+", choices=list(eng.ENGINES), default=list(eng.ENGINES)
    )
    p.add_argument("-l", "--langs", nargs="+", help="language keys from sentences.json")
    p.add_argument("-o", "--out", type=Path, default=Path("bench-out"))
    p.add_argument("--no-asr", action="store_true", help="skip the Whisper intelligibility check")
    p.add_argument(
        "--rescore", action="store_true", help="rerun the Whisper check on the clips in --out"
    )
    p.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "psittacus-bench")
    args = p.parse_args()

    sentences = json.loads((HERE / "sentences.json").read_text(encoding="utf-8"))
    voices = json.loads((HERE / "voices.json").read_text(encoding="utf-8"))
    results = args.out / "results.json"
    if args.rescore:
        saved = json.loads(results.read_text(encoding="utf-8"))
        infos, rows = saved["engines"], saved["rows"]
    else:
        jobs = plan(sentences, voices, args.engines, args.langs)
        args.out.mkdir(parents=True, exist_ok=True)
        infos, rows = [], []
        for name in args.engines:
            print(f"{name}:")
            mine = [j for j in jobs if j["engine"] == name]
            info, got = run_engine(eng.ENGINES[name](args.cache), mine, args.out)
            infos.append(info)
            rows += got
        results.write_text(json.dumps({"engines": infos, "rows": rows}, indent=1))

    if not args.no_asr:
        check(rows, sentences, args.out)
    if args.langs:
        sentences = {k: v for k, v in sentences.items() if k in args.langs}
    machine = f"{platform.system()} {platform.machine()}, {platform.processor() or 'CPU'}"
    page = report.render(sentences, infos, rows, machine)
    (args.out / "index.html").write_text(page, encoding="utf-8")
    results.write_text(json.dumps({"engines": infos, "rows": rows}, indent=1))
    print(f"wrote {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
