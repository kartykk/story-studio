#!/usr/bin/env python3
"""
Non-interactive story pipeline benchmark (no ElevenLabs).

Usage:
  python scripts/run_story_benchmark.py --phase smoke
  python scripts/run_story_benchmark.py --phase full
  python scripts/run_story_benchmark.py --report-only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from core.story_bible import StoryBible
from core.story_writer import (
    select_language,
    develop_premise,
    generate_titles,
    set_title,
    build_world,
    build_character,
    generate_beats,
    plan_chapters,
    draft_chapter_scenes,
    write_chapter_gated,
)
from core.interest_scorer import (
    score_chapter_scenes_from_prose,
    validate_interest_curve,
)
from core.quality_gate import (
    _check_chapter_ending_hook,
    _genre_rule_violations,
)
from core.emotion_scorer import score_text, emotion_consistency

from main import detect_genre, get_genre_model

OUTPUT_DIR = ROOT / "output"
NUM_CHAPTERS = 4
NUM_SCENES = 2

SMOKE_CASES = [
    {
        "story_id": "test-crime-en",
        "genre": "crime",
        "language": "English",
        "premise": "A corrupt cop investigates a murder in Mumbai that leads to his own precinct.",
        "roles": ("detective", "criminal"),
    },
    {
        "story_id": "test-romance-hi",
        "genre": "romance",
        "language": "Hindi",
        "premise": "दिल्ली में दो परिवारों के बीच प्रतिबंधित प्रेम कहानी — दुश्मनी से प्यार तक।",
        "roles": ("protagonist", "love interest"),
    },
]

FULL_CASES = [
    {
        "story_id": "bench-crime-en",
        "genre": "crime",
        "language": "English",
        "premise": "Mumbai noir: a detective uncovers corruption while hunting a serial killer.",
        "roles": ("detective", "killer"),
    },
    {
        "story_id": "bench-romance-hi",
        "genre": "romance",
        "language": "Hindi",
        "premise": "जयपुर में दुश्मन-से-प्रेमी: दो रival परिवारों के बच्चों की मिलन कहानी।",
        "roles": ("protagonist", "love interest"),
    },
    {
        "story_id": "bench-horror-es",
        "genre": "horror",
        "language": "Spanish",
        "premise": "Un pueblo rural de México está maldito — fantasmas del pasado regresan cada luna llena.",
        "roles": ("protagonist", "antagonist"),
    },
    {
        "story_id": "bench-fantasy-en",
        "genre": "fantasy",
        "language": "English",
        "premise": "The chosen one must save a dying kingdom from an ancient shadow curse.",
        "roles": ("hero", "mentor"),
    },
    {
        "story_id": "bench-literary-en",
        "genre": "literary",
        "language": "English",
        "premise": "A coming-of-age memory piece about family, identity, and Kolkata monsoons.",
        "roles": ("protagonist", "mentor"),
    },
]


@dataclass
class StageResult:
    name: str
    ok: bool
    seconds: float
    error: str = ""


def _detect_script(text: str) -> dict:
    devanagari = len(re.findall(r"[\u0900-\u097F]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    spanish_markers = len(re.findall(r"[áéíóúñ¿¡]", text, re.I))
    return {
        "devanagari_chars": devanagari,
        "latin_chars": latin,
        "spanish_marker_chars": spanish_markers,
        "primary": (
            "devanagari" if devanagari > latin else
            "spanish" if spanish_markers > 5 else
            "latin" if latin > 0 else "unknown"
        ),
    }


def _language_ok(language: str, chapter_text: str) -> bool:
    scripts = _detect_script(chapter_text)
    lang = language.lower()
    if lang == "hindi":
        return scripts["devanagari_chars"] >= 20
    if lang == "spanish":
        return scripts["latin_chars"] >= 50
    if lang == "english":
        return scripts["latin_chars"] >= 50 and scripts["devanagari_chars"] < 20
    return scripts["latin_chars"] >= 30


def _run_stage(name: str, fn) -> tuple[StageResult, object | None]:
    t0 = time.perf_counter()
    try:
        result = fn()
        return StageResult(name, True, time.perf_counter() - t0), result
    except Exception as e:
        return StageResult(name, False, time.perf_counter() - t0, str(e)), None


def run_test_case(case: dict) -> dict:
    story_id = case["story_id"]
    expected_genre = case["genre"]
    language = case["language"]
    premise = case["premise"]
    roles = case["roles"]

    print(f"\n{'='*60}\n  Running: {story_id} ({expected_genre} / {language})\n{'='*60}")

    detected = detect_genre(premise)
    genre_model = get_genre_model(expected_genre)
    bible = StoryBible(story_id)

    stages: list[StageResult] = []
    chapter_text = ""
    quality_report = None
    fatal_error = ""

    def _stage(name, fn):
        nonlocal fatal_error
        sr, val = _run_stage(name, fn)
        stages.append(sr)
        status = "OK" if sr.ok else f"FAIL: {sr.error}"
        print(f"  [{sr.seconds:6.1f}s] {name}: {status}")
        if not sr.ok and not fatal_error:
            fatal_error = f"{name}: {sr.error}"
        return val

    _stage("language", lambda: select_language(bible, language))
    _stage("premise", lambda: develop_premise(bible, premise, genre_model))
    bible.genre_model_name = expected_genre

    titles = _stage("titles", lambda: generate_titles(bible))
    if titles:
        set_title(bible, titles[0] if isinstance(titles, list) else bible.title_candidates[0])

    _stage("world", lambda: build_world(bible, genre_model))
    _stage("character_1", lambda: build_character(bible, roles[0], tier=1, genre_model=genre_model))
    _stage("character_2", lambda: build_character(bible, roles[1], tier=1, genre_model=genre_model))
    _stage("beats", lambda: generate_beats(bible))
    _stage("chapter_plan", lambda: plan_chapters(bible, NUM_CHAPTERS, genre_model))
    _stage("scene_drafts", lambda: draft_chapter_scenes(bible, 1, NUM_SCENES, genre_model))

    cp = bible.get_chapter_plan(1)
    scene_scores = []
    if cp and cp.scene_interest_scores:
        from core.interest_scorer import SceneInterestScore
        scene_scores = [SceneInterestScore(sis_total=s) for s in cp.scene_interest_scores]

    def _write():
        nonlocal chapter_text, quality_report
        chapter_text, quality_report = write_chapter_gated(
            bible, 1, genre_model=genre_model, scene_scores=scene_scores
        )
        return chapter_text

    if not fatal_error:
        _stage("write_chapter_gated", _write)

    # Post-write metrics
    sis_scores, curve_warnings = [], []
    hook_ok, hook_issue = False, ""
    genre_violations = []
    emotion_info = {}

    if chapter_text:
        sis_scores, curve_warnings = score_chapter_scenes_from_prose(chapter_text, cp, genre_model)
        hook_ok, hook_issue = _check_chapter_ending_hook(chapter_text)
        genre_violations = _genre_rule_violations(bible, genre_model, 1, chapter_text)
        try:
            emo = score_text(chapter_text[:2000])
            emotion_info = {
                "dominant": emo.dominant_emotion,
                "intensity": round(emo.intensity, 3),
                "consistency": round(
                    emotion_consistency(emo, cp.target_emotions if cp else {}), 3
                ) if cp else None,
            }
        except Exception as e:
            emotion_info = {"error": str(e)}

    scripts = _detect_script(chapter_text) if chapter_text else {}
    lang_ok = _language_ok(language, chapter_text) if chapter_text else False

    qr = quality_report
    result = {
        "story_id": story_id,
        "expected_genre": expected_genre,
        "detected_genre": detected,
        "language": language,
        "premise": premise,
        "title": bible.title,
        "logline": bible.logline,
        "arc_type": bible.emotional_arc_type,
        "fatal_error": fatal_error,
        "stages": [asdict(s) for s in stages],
        "total_seconds": round(sum(s.seconds for s in stages), 1),
        "setup_ok": not fatal_error,
        "chapter_written": bool(chapter_text),
        "word_count": len(chapter_text.split()) if chapter_text else 0,
        "excerpt": chapter_text[:300] if chapter_text else "",
        "quality": {
            "total_score": qr.total_score if qr else None,
            "threshold": qr.threshold if qr else genre_model.quality_threshold,
            "passed": qr.passed if qr else False,
            "attempt": qr.attempt if qr else None,
            "axes": {
                "emotional_resonance": qr.emotional_resonance.score if qr else None,
                "narrative_craft": qr.narrative_craft.score if qr else None,
                "pacing": qr.pacing.score if qr else None,
                "character_auth": qr.character_auth.score if qr else None,
                "genre_adherence": qr.genre_adherence.score if qr else None,
            },
            "top_issues": qr.top_issues if qr else [],
        },
        "sis": {
            "avg": round(sum(s.sis_total for s in sis_scores) / len(sis_scores), 1) if sis_scores else None,
            "scene_count": len(sis_scores),
            "curve_warnings": curve_warnings,
        },
        "hook": {"ok": hook_ok, "issue": hook_issue},
        "genre_violations": genre_violations,
        "emotion": emotion_info,
        "language_check": {"ok": lang_ok, "scripts": scripts},
    }
    return result


def render_markdown(report: dict) -> str:
    phase = report["phase"]
    ts = report["timestamp"]
    results = report["results"]
    lines = [
        f"# Story Studio Benchmark Report",
        f"",
        f"**Phase:** {phase}  ",
        f"**Run at:** {ts}  ",
        f"**Stories:** {len(results)}  ",
        f"",
    ]

    ok_setup = sum(1 for r in results if r["setup_ok"])
    ok_chapter = sum(1 for r in results if r["chapter_written"])
    passed = sum(1 for r in results if r["quality"].get("passed"))
    scores = [r["quality"]["total_score"] for r in results if r["quality"]["total_score"] is not None]
    sis_avgs = [r["sis"]["avg"] for r in results if r["sis"]["avg"] is not None]
    total_time = sum(r["total_seconds"] for r in results)

    lines += [
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Setup success | {ok_setup}/{len(results)} |",
        f"| Chapter 1 written | {ok_chapter}/{len(results)} |",
        f"| Quality gate passed | {passed}/{len(results)} |",
        f"| Avg quality score | {sum(scores)/len(scores):.1f}" if scores else "| Avg quality score | N/A |",
        f"| Avg SIS | {sum(sis_avgs)/len(sis_avgs):.1f}" if sis_avgs else "| Avg SIS | N/A |",
        f"| Total wall time | {total_time:.0f}s |",
        "",
        "## Per-Story Results",
        "",
        "| Story | Genre | Lang | Quality | Pass | Words | SIS | Hook | Lang OK |",
        "|-------|-------|------|---------|------|-------|-----|------|---------|",
    ]

    for r in results:
        q = r["quality"]
        lines.append(
            f"| {r['story_id']} | {r['expected_genre']} | {r['language']} | "
            f"{q['total_score'] or '—'} | {'PASS' if q['passed'] else 'FAIL'} | "
            f"{r['word_count']} | {r['sis']['avg'] or '—'} | "
            f"{'Y' if r['hook']['ok'] else 'N'} | {'Y' if r['language_check']['ok'] else 'N'} |"
        )

    lines += ["", "## Axis Averages", ""]
    axes = ["emotional_resonance", "narrative_craft", "pacing", "character_auth", "genre_adherence"]
    for ax in axes:
        vals = [r["quality"]["axes"][ax] for r in results if r["quality"]["axes"][ax] is not None]
        avg = sum(vals) / len(vals) if vals else 0
        lines.append(f"- **{ax.replace('_', ' ').title()}:** {avg:.1f}")

    lines += ["", "## Issues & Warnings", ""]
    for r in results:
        issues = []
        if r["fatal_error"]:
            issues.append(f"FATAL: {r['fatal_error']}")
        issues.extend(r["quality"].get("top_issues") or [])
        issues.extend(r["sis"].get("curve_warnings") or [])
        issues.extend(r["genre_violations"])
        if not r["hook"]["ok"] and r["hook"]["issue"]:
            issues.append(r["hook"]["issue"])
        if not r["language_check"]["ok"]:
            issues.append(f"Language check failed (expected {r['language']})")
        lines.append(f"### {r['story_id']}")
        if issues:
            for i in issues:
                lines.append(f"- {i}")
        else:
            lines.append("- No issues")
        lines.append("")

    lines += ["## Sample Excerpts", ""]
    for r in results:
        lines.append(f"### {r['story_id']} — {r['title']}")
        lines.append(f"> {r['excerpt'].replace(chr(10), ' ')[:300]}...")
        lines.append("")

    lines += ["## Recommendations", ""]
    if passed < len(results):
        lines.append("- Some chapters failed the quality gate — review `top_issues` and consider threshold tuning.")
    lang_fails = [r for r in results if not r["language_check"]["ok"] and r["chapter_written"]]
    if lang_fails:
        lines.append(f"- Language output mismatch in: {', '.join(r['story_id'] for r in lang_fails)}.")
    if not any(r["emotion"].get("dominant") for r in results):
        lines.append("- Emotion scoring may be degraded — verify DEEPSEEK_API_KEY.")
    if ok_setup == len(results) and ok_chapter == len(results):
        lines.append("- Pipeline stable — safe to run full benchmark or longer chapters.")

    return "\n".join(lines)


def run_benchmark(phase: str) -> tuple[Path, Path]:
    cases = SMOKE_CASES if phase == "smoke" else FULL_CASES
    results = [run_test_case(c) for c in cases]

    report = {
        "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"benchmark_{phase}_{ts_slug}.json"
    md_path = OUTPUT_DIR / f"benchmark_{phase}_{ts_slug}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))

    print(f"\n  Report saved:")
    print(f"    JSON: {json_path}")
    print(f"    MD:   {md_path}")
    return json_path, md_path


def report_only():
    files = sorted(OUTPUT_DIR.glob("benchmark_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("No benchmark JSON found in output/")
        return
    with open(files[0], encoding="utf-8") as f:
        report = json.load(f)
    md = render_markdown(report)
    md_path = files[0].with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n  Re-rendered: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Story Studio benchmark runner")
    parser.add_argument("--phase", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    if args.report_only:
        report_only()
        return

    try:
        run_benchmark(args.phase)
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
