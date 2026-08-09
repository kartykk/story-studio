"""
main.py — Story Studio CLI entry point.

Genre auto-detection → routes to specialized genre model → full pipeline.

Usage:
  python main.py new                     # start a new story
  python main.py load <story_id>         # continue existing story
  python main.py list                    # list all stories
  python main.py write <story_id> <ch>   # write specific chapter
  python main.py quality <story_id> <ch> # score chapter quality
  python main.py interest <story_id> <ch># show scene interest report
  python main.py audio <story_id> <ch>   # generate chapter audio
  python main.py video <story_id> <ch>   # generate chapter video
  python main.py export <story_id>       # export full story as text
"""

import sys
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from core.story_bible import StoryBible, CharacterProfile
from core.story_writer import (
    SUPPORTED_LANGUAGES, select_language, develop_premise,
    generate_titles, set_title, build_world, build_character,
    generate_beats, plan_chapters, draft_chapter_scenes,
    write_chapter, write_chapter_gated, refine_chapter, ask_question,
)
from core.arc_calculator import REAGAN_ARC_TYPES, ARC_DESCRIPTIONS, suggest_arc_type
from core.interest_scorer import scene_interest_report

# ── Genre Models ──────────────────────────────────────────────────────────────

from genres.crime.writer    import CrimeGenreModel
from genres.romance.writer  import RomanceGenreModel
from genres.horror.writer   import HorrorGenreModel
from genres.fantasy.writer  import FantasyGenreModel
from genres.literary.writer import LiteraryGenreModel

GENRE_MODELS = {
    "crime":    CrimeGenreModel(),
    "romance":  RomanceGenreModel(),
    "horror":   HorrorGenreModel(),
    "fantasy":  FantasyGenreModel(),
    "literary": LiteraryGenreModel(),
}

GENRE_KEYWORDS = {
    "crime":    ["crime", "murder", "detective", "thriller", "mystery", "heist", "noir",
                 "police", "corruption", "investigation", "killer", "suspect", "forensic"],
    "romance":  ["romance", "love", "relationship", "love story", "enemies", "forbidden",
                 "second chance", "wedding", "heart", "couple", "attraction"],
    "horror":   ["horror", "scary", "ghost", "demon", "fear", "haunted", "monster",
                 "supernatural", "dark", "evil", "terror", "nightmare", "creature"],
    "fantasy":  ["fantasy", "magic", "wizard", "dragon", "quest", "chosen", "kingdom",
                 "spell", "mythical", "enchanted", "sorcerer", "elves", "dwarves", "mage"],
    "literary": ["literary", "character study", "slice of life", "coming of age",
                 "social", "psychological", "family", "identity", "memory"],
}


def detect_genre(user_input: str) -> str:
    """Auto-detect genre from user description. Falls back to literary."""
    user_lower = user_input.lower()
    scores = {}
    for genre, keywords in GENRE_KEYWORDS.items():
        scores[genre] = sum(1 for kw in keywords if kw in user_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "literary"


def get_genre_model(genre: str):
    return GENRE_MODELS.get((genre or "").lower(), GENRE_MODELS["literary"])


# ── Display Helpers ───────────────────────────────────────────────────────────

def _parse_chapter_num(value: str) -> int | None:
    try:
        n = int(value)
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def _separator():
    print("\n" + "─" * 65 + "\n")


def _header(title: str):
    print("\n" + "═" * 65)
    print(f"  {title}")
    print("═" * 65 + "\n")


def _prompt(message: str) -> str:
    return input(f"  → {message}: ").strip()


def _yn(message: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    answer = input(f"  → {message} [{default_str}]: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _choose(options: list, prompt: str = "Choose") -> str:
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        try:
            choice = int(_prompt(f"{prompt} (1-{len(options)})"))
            if 1 <= choice <= len(options):
                return options[choice - 1]
        except (ValueError, TypeError):
            pass
        print("    Invalid choice. Try again.")


# ── Stage Runner ──────────────────────────────────────────────────────────────

def run_new_story():
    """Full interactive new story pipeline."""
    _header("Story Studio — New Story")

    # Stage 0: Language
    print("  Step 0: Language Selection")
    print(f"  Supported: {', '.join(list(SUPPORTED_LANGUAGES.keys())[:8])} (and more)")
    lang = _prompt("Write story in (default: English)") or "English"

    story_id = _prompt("Story ID (short slug, e.g. 'mumbai-noir')").replace(" ", "_")
    if not story_id:
        story_id = "story_" + lang.lower()[:3]

    bible = StoryBible(story_id)
    select_language(bible, lang)
    print(f"  Language set: {bible.language} ({bible.language_code})")

    # Stage 1: Premise
    _separator()
    print("  Step 1: Story Premise")
    print("  Tell me your story idea. Be as brief or detailed as you like.")
    print("  Example: 'I want a crime story about a corrupt cop in Mumbai'")
    raw = _prompt("Your story concept")

    detected = detect_genre(raw)
    genre_model = get_genre_model(detected)
    print(f"\n  Detected genre: {genre_model.genre_display_name()}")
    confirm = _yn(f"Use {genre_model.genre_display_name()} model?")
    if not confirm:
        print("  Available genres:")
        chosen_genre = _choose(list(GENRE_MODELS.keys()), "Genre")
        genre_model = get_genre_model(chosen_genre)

    print(f"\n  Developing premise...")
    develop_premise(bible, raw, genre_model)
    bible.genre_model_name = genre_model.genre

    print(f"  Logline:  {bible.logline}")
    print(f"  Theme:    {bible.theme}")
    print(f"  Tone:     {bible.tone}")
    print(f"  Arc type: {bible.emotional_arc_type}")

    if not _yn("Continue with this premise?"):
        custom = _prompt("Describe what to change")
        develop_premise(bible, f"{raw}. Additional guidance: {custom}", genre_model)
        print(f"  New logline: {bible.logline}")

    # Stage 2: Title
    _separator()
    print("  Step 2: Title Selection")
    print("  Generating 5 title options...")
    titles = generate_titles(bible)
    print()
    for i, t in enumerate(titles, 1):
        print(f"    {i}. {t}")
    print(f"    6. Enter my own title")

    chosen = _prompt("Choose title (1-6)")
    if chosen == "6" or not chosen.isdigit():
        title = _prompt("Your title")
    else:
        try:
            title = titles[int(chosen) - 1]
        except (IndexError, ValueError):
            title = _prompt("Your title")

    set_title(bible, title)
    print(f"  Title set: {bible.title}")

    # Stage 3: World
    _separator()
    print("  Step 3: World Building")
    print("  Building world bible...")
    build_world(bible, genre_model)
    print(f"  World: {bible.world.overview[:120]}...")

    # Stage 4: Characters
    _separator()
    print("  Step 4: Characters")
    char_count = genre_model.suggested_character_count()
    print(f"  Recommended for {genre_model.genre_display_name()}:")
    print(f"    Tier 1 (full psychological profile): {char_count['tier1']}")
    print(f"    Tier 2 (supporting):                {char_count['tier2']}")
    print(f"    Tier 3 (minor):                     {char_count['tier3']}")

    total_tier1 = char_count.get("tier1", 2)
    for i in range(total_tier1):
        role = _prompt(f"Tier 1 character {i+1} — role (e.g. detective, protagonist)")
        print(f"  Building Tier 1 character: {role}...")
        char = build_character(bible, role, tier=1, genre_model=genre_model)
        print(f"  Created: {char.name} ({char.role})")

    add_more = _yn(f"Add supporting characters (Tier 2)?")
    tier2_count = 0
    while add_more and tier2_count < char_count.get("tier2", 3):
        role = _prompt("Tier 2 character role")
        char = build_character(bible, role, tier=2, genre_model=genre_model)
        print(f"  Created: {char.name} ({char.role})")
        tier2_count += 1
        add_more = _yn("Add another Tier 2 character?") if tier2_count < char_count.get("tier2", 3) else False

    add_minor = _yn("Add minor characters (Tier 3)?")
    tier3_count = 0
    while add_minor and tier3_count < char_count.get("tier3", 5):
        role = _prompt("Minor character role")
        char = build_character(bible, role, tier=3, genre_model=genre_model)
        print(f"  Created: {char.name}")
        tier3_count += 1
        add_minor = _yn("Add another?") if tier3_count < char_count.get("tier3", 5) else False

    # Stage 5: Beats
    _separator()
    print("  Step 5: Story Beats")
    print("  Generating Save the Cat 15 beats...")
    generate_beats(bible)
    print(f"  Generated {len(bible.beats)} beats.")
    if _yn("Show beats?"):
        print("\n" + bible.beats_for_prompt())

    # Stage 6: Chapter Plan
    _separator()
    print("  Step 6: Chapter Plan")
    try:
        num_chapters = int(_prompt("How many chapters? (default: 12)") or "12")
    except ValueError:
        num_chapters = 12

    print(f"  Planning {num_chapters} chapters...")
    plan_chapters(bible, num_chapters, genre_model)
    print(f"  Chapter plan created.")
    if _yn("Show chapter plan?"):
        print("\n" + bible.chapter_plan_for_prompt())

    _separator()
    print(f"  Story '{bible.title}' (ID: {story_id}) is ready!")
    print(f"  Genre: {genre_model.genre_display_name()} | Arc: {bible.emotional_arc_type}")
    print(f"  {len(bible.characters)} characters | {len(bible.chapter_plan)} chapters")
    print(f"\n  To write:")
    print(f"    python main.py write {story_id} 1")


def run_write_chapter(story_id: str, chapter_num: int):
    bible = StoryBible.load(story_id)
    genre_model = get_genre_model(bible.genre_model_name or bible.genre)
    cp = bible.get_chapter_plan(chapter_num)

    if not cp:
        print(f"  No chapter plan for chapter {chapter_num}")
        return

    _header(f"Writing Chapter {chapter_num}: {cp.title}")
    print(f"  Summary: {cp.summary}")
    print(f"  Goal: {cp.emotional_goal}")

    if not cp.scenes and _yn("Draft scenes first (recommended)?"):
        try:
            scene_count = int(_prompt("Scenes per chapter (default: 3)") or "3")
        except ValueError:
            scene_count = 3
        print(f"  Drafting scenes...")
        scene_drafts = draft_chapter_scenes(bible, chapter_num, scene_count, genre_model)
        for sd in scene_drafts:
            print(f"\n  Scene {sd.scene_number} (SIS={sd.sis_estimate:.0f}, {sd.word_count_target}w, {sd.narrative_mode}):")
            print(f"    {sd.brief_description}")
        if not _yn("Approve and write?"):
            print("  Saved. Re-run to write chapter.")
            return
        cp.draft_approved = True
        bible.save()

    from core.interest_scorer import SceneInterestScore
    scene_scores = [SceneInterestScore(sis_total=s) for s in (cp.scene_interest_scores or [])]

    use_gate = _yn("Use quality gate (auto-retry)?", default=True)
    if use_gate:
        print(f"  Writing (quality threshold: {genre_model.quality_threshold}/100)...")
        chapter_text, report = write_chapter_gated(
            bible, chapter_num, genre_model=genre_model, scene_scores=scene_scores
        )
        print(report.summary())
    else:
        pivotal_beats = {9, 11, 12, 14}
        use_thinking = any(b in pivotal_beats for b in cp.beats_covered)
        chapter_text = write_chapter(
            bible, chapter_num, genre_model=genre_model,
            scene_scores=scene_scores, use_thinking=use_thinking,
        )

    print(f"\n  Chapter {chapter_num} done. ({len(chapter_text.split())} words)")


def run_quality_check(story_id: str, chapter_num: int):
    from core.quality_gate import score_chapter_quality
    from core.emotion_scorer import score_text

    bible = StoryBible.load(story_id)
    genre_model = get_genre_model(bible.genre_model_name or bible.genre)
    chapter = bible.get_chapter(chapter_num)
    if not chapter:
        print(f"  Chapter {chapter_num} not written.")
        return

    _header(f"Quality Check — Chapter {chapter_num}")
    emotion_score = None
    try:
        emotion_score = score_text(chapter["content"][:2000])
        print(f"  Dominant emotion: {emotion_score.dominant_emotion} ({emotion_score.intensity:.0%})")
    except Exception:
        pass

    cp = bible.get_chapter_plan(chapter_num)
    report = score_chapter_quality(
        chapter_text=chapter["content"],
        chapter_number=chapter_num,
        total_chapters=len(bible.chapter_plan) or 10,
        genre=genre_model.genre,
        emotional_goal=cp.emotional_goal if cp else "",
        target_emotions=cp.target_emotions if cp else {},
        emotion_score=emotion_score,
        character_summaries=bible.character_compact_list(),
    )
    print(report.summary())


def run_interest_report(story_id: str, chapter_num: int):
    from core.interest_scorer import score_scene, scene_interest_report

    bible = StoryBible.load(story_id)
    genre_model = get_genre_model(bible.genre_model_name or bible.genre)
    cp = bible.get_chapter_plan(chapter_num)
    if not cp or not cp.scenes:
        print(f"  No scene drafts for chapter {chapter_num}.")
        return

    _header(f"Scene Interest Report — Chapter {chapter_num}")
    scene_scores = []
    previous = []
    for sd_data in cp.scenes:
        sis = score_scene(
            scene_draft=sd_data.get("brief_description", ""),
            beats_covered=sd_data.get("beats_covered", []),
            position_pct=cp.position_pct,
            previous_scores=previous,
            target_emotions=cp.target_emotions,
        )
        scene_scores.append(sis)
        previous.append(sis)
    print(scene_interest_report(scene_scores))


def run_generate_audio(story_id: str, chapter_num: int):
    from core.voice_engine import generate_chapter_audio
    from core.dialogue_parser import parse_story_into_segments

    bible = StoryBible.load(story_id)
    chapter = bible.get_chapter(chapter_num)
    if not chapter:
        print(f"  Chapter {chapter_num} not written.")
        return

    _header(f"Generating Audio — Chapter {chapter_num}")
    score_emotions = _yn("Score emotions per segment?", default=False)
    segments = parse_story_into_segments(chapter["content"], bible, score_emotions=score_emotions)
    print(f"  {len(segments)} segments found.")
    output = generate_chapter_audio(bible, chapter_num, segments)
    print(f"  Audio: {output}")


def run_generate_video(story_id: str, chapter_num: int):
    from core.voice_engine import generate_chapter_audio
    from core.video_engine import generate_chapter_video
    from core.dialogue_parser import parse_story_into_segments

    bible = StoryBible.load(story_id)
    chapter = bible.get_chapter(chapter_num)
    if not chapter:
        print(f"  Chapter {chapter_num} not written.")
        return

    _header(f"Generating Video — Chapter {chapter_num}")
    segments = parse_story_into_segments(chapter["content"], bible)
    audio_path, segment_files, valid_segments = generate_chapter_audio(
        bible, chapter_num, segments, return_segment_files=True
    )

    cp = bible.get_chapter_plan(chapter_num)
    video_path = generate_chapter_video(
        bible=bible,
        chapter_number=chapter_num,
        segments=valid_segments,
        segment_audio_files=segment_files,
        chapter_title=cp.title if cp else f"Chapter {chapter_num}",
        on_progress=lambda msg: print(f"    {msg}"),
    )
    print(f"  Video: {video_path}")


OUTPUT_DIR = Path(__file__).parent / "output"


def run_export(story_id: str):
    bible = StoryBible.load(story_id)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{story_id}_export.txt"
    with open(output_path, "w") as f:
        f.write(f"{bible.title}\n{'=' * len(bible.title)}\n\n")
        f.write(f"Logline: {bible.logline}\nTheme: {bible.theme}\n\n")
        for chapter in sorted(bible.chapters, key=lambda c: c["number"]):
            f.write(chapter["content"] + "\n\n")
    print(f"  Exported: {output_path}")


def run_list():
    stories = StoryBible.list_stories()
    if not stories:
        print("  No stories found.")
        return
    print(f"\n  Stories ({len(stories)}):")
    for s in stories:
        try:
            b = StoryBible.load(s)
            cw = len(b.chapters)
            ct = len(b.chapter_plan)
            genre = b.genre_model_name or b.genre or "?"
            print(f"    {s:<30} {(b.title or '(untitled)'):<35} {genre:<12} Ch: {cw}/{ct}")
        except Exception:
            print(f"    {s}")


def run_load_story(story_id: str):
    bible = StoryBible.load(story_id)
    genre_model = get_genre_model(bible.genre_model_name or bible.genre)

    _header(f"Continue: {bible.title}")
    print(f"  Genre: {genre_model.genre_display_name()} | Chapters: {len(bible.chapters)}/{len(bible.chapter_plan)}")
    print(f"  Written: {bible.chapters_written_summary()}")
    print(f"\n  Commands: write <N> | quality <N> | interest <N> | ask | refine <N> | audio <N> | video <N> | export | quit")

    while True:
        cmd = _prompt("\nCommand").split()
        if not cmd:
            continue
        action = cmd[0].lower()

        if action in ("quit", "exit", "q"):
            break
        elif action == "write" and len(cmd) > 1:
            ch = _parse_chapter_num(cmd[1])
            if ch:
                run_write_chapter(story_id, ch)
            else:
                print("  Invalid chapter number.")
        elif action == "quality" and len(cmd) > 1:
            ch = _parse_chapter_num(cmd[1])
            if ch:
                run_quality_check(story_id, ch)
            else:
                print("  Invalid chapter number.")
        elif action == "interest" and len(cmd) > 1:
            ch = _parse_chapter_num(cmd[1])
            if ch:
                run_interest_report(story_id, ch)
            else:
                print("  Invalid chapter number.")
        elif action == "ask":
            q = _prompt("Question")
            print(f"\n  {ask_question(bible, q, genre_model)}\n")
        elif action == "refine" and len(cmd) > 1:
            ch = _parse_chapter_num(cmd[1])
            if not ch:
                print("  Invalid chapter number.")
                continue
            feedback = _prompt("Feedback")
            refine_chapter(bible, ch, feedback)
            print("  Refined.")
        elif action == "export":
            run_export(story_id)
        elif action == "audio" and len(cmd) > 1:
            ch = _parse_chapter_num(cmd[1])
            if ch:
                run_generate_audio(story_id, ch)
            else:
                print("  Invalid chapter number.")
        elif action == "video" and len(cmd) > 1:
            ch = _parse_chapter_num(cmd[1])
            if ch:
                run_generate_video(story_id, ch)
            else:
                print("  Invalid chapter number.")
        else:
            print(f"  Unknown: {action}")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "new":
        run_new_story()
    elif cmd == "list":
        run_list()
    elif cmd == "load" and len(args) >= 2:
        run_load_story(args[1])
    elif cmd == "write" and len(args) >= 3:
        ch = _parse_chapter_num(args[2])
        if ch:
            run_write_chapter(args[1], ch)
        else:
            print("  Invalid chapter number.")
    elif cmd == "quality" and len(args) >= 3:
        ch = _parse_chapter_num(args[2])
        if ch:
            run_quality_check(args[1], ch)
        else:
            print("  Invalid chapter number.")
    elif cmd == "interest" and len(args) >= 3:
        ch = _parse_chapter_num(args[2])
        if ch:
            run_interest_report(args[1], ch)
        else:
            print("  Invalid chapter number.")
    elif cmd == "audio" and len(args) >= 3:
        ch = _parse_chapter_num(args[2])
        if ch:
            run_generate_audio(args[1], ch)
        else:
            print("  Invalid chapter number.")
    elif cmd == "video" and len(args) >= 3:
        ch = _parse_chapter_num(args[2])
        if ch:
            run_generate_video(args[1], ch)
        else:
            print("  Invalid chapter number.")
    elif cmd == "export" and len(args) >= 2:
        run_export(args[1])
    else:
        print(f"Unknown command: {' '.join(args)}\nRun 'python main.py help' for usage.")


if __name__ == "__main__":
    main()
