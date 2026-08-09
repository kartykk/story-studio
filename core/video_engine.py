"""
core/video_engine.py — FFmpeg-based video generation for Story Studio.

Updated imports: uses core.story_bible, core.dialogue_parser.

Pipeline per chapter:
  1. Each dialogue/narration segment → apply voice effect → effected audio
  2. Measure audio duration
  3. Render video frame (background + character name + dialogue text)
  4. Concatenate all clips → chapter video
  5. Add intro title card + outro fade

Voice Effects (auto-detected from character description):
  villain / dark / evil / demon   → deep pitch + subtle distortion
  ghost / spirit / ethereal       → heavy reverb + slight pitch up
  child / young / little          → pitch up + bright tone
  robot / machine / android       → robotic flanger + stutter
  elder / ancient / wise / old    → slow + deep + warm reverb
  narrator                        → clear, slight warmth + compression
  default                         → clean + light compression
"""

import os
import re
import json
import subprocess
import textwrap
import tempfile
from pathlib import Path
from dataclasses import dataclass

from core.story_bible import StoryBible, CharacterProfile
from core.dialogue_parser import Segment


OUTPUT_DIR = Path(__file__).parent.parent / "output"
AUDIO_DIR  = Path(__file__).parent.parent / "audio"
FONTS_DIR  = Path(__file__).parent.parent / "fonts"

VIDEO_W = 1920
VIDEO_H = 1080
FPS     = 24

# Genre → background color scheme (dark bg, accent color)
GENRE_COLORS = {
    "fantasy":     ("0x0a0718", "0x9b59f5"),
    "horror":      ("0x080808", "0xcc0000"),
    "sci-fi":      ("0x020d1a", "0x00d4ff"),
    "romance":     ("0x1a0a0f", "0xff6b9d"),
    "crime":       ("0x080c0a", "0xf0c040"),
    "thriller":    ("0x080c0a", "0x00ff88"),
    "mystery":     ("0x0d0d14", "0xf0c040"),
    "adventure":   ("0x0a1208", "0x40c840"),
    "historical":  ("0x120e08", "0xd4a030"),
    "literary":    ("0x0c0c10", "0xaaaacc"),
    "default":     ("0x0a0a12", "0x6080ff"),
}

# Voice effects chains for FFmpeg -af filter
VOICE_EFFECTS = {
    "villain":  "asetrate=44100*0.88,atempo=1.13,aecho=0.5:0.4:80:0.25,bass=g=4",
    "ghost":    "aecho=0.85:0.85:600:0.6,aecho=0.6:0.6:300:0.3,atempo=0.93,treble=g=-3",
    "child":    "asetrate=44100*1.18,atempo=0.85,treble=g=5",
    "robot":    "afftdn=nf=-20,aecho=0.3:0.3:8:0.5,flanger=delay=5:depth=3:speed=0.5",
    "elder":    "asetrate=44100*0.92,atempo=1.09,aecho=0.4:0.4:200:0.2,bass=g=3",
    "spirit":   "aecho=0.9:0.9:800:0.7,aphaser=type=t:speed=0.4,atempo=0.96",
    "narrator": "acompressor=threshold=-18dB:ratio=3:attack=5:release=50,treble=g=2",
    "default":  "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=50",
}


# ── Voice Effect Detection ────────────────────────────────────────────────────

def detect_voice_effect(speaker: str, bible: StoryBible) -> str:
    """Auto-detect which voice effect to apply based on character description."""
    if speaker == "narrator":
        return VOICE_EFFECTS["narrator"]

    char = bible.get_character(speaker)
    desc = (char.physical_description if char else "").lower()
    role = (char.role if char else "").lower()
    combined = f"{desc} {role}"

    keywords = {
        "villain": ["villain", "evil", "dark", "demon", "corrupt", "wicked", "sinister", "antagonist"],
        "ghost":   ["ghost", "spirit", "specter", "undead", "wraith", "phantom"],
        "spirit":  ["ethereal", "mystical", "celestial", "divine", "angelic", "astral"],
        "child":   ["child", "young", "kid", "little", "boy", "girl", "teen", "juvenile"],
        "robot":   ["robot", "android", "machine", "ai", "synthetic", "cyborg", "mechanical"],
        "elder":   ["elder", "old", "ancient", "wise", "aged", "patriarch", "matriarch", "sage"],
    }

    for effect_key, words in keywords.items():
        if any(w in combined for w in words):
            return VOICE_EFFECTS[effect_key]

    return VOICE_EFFECTS["default"]


# ── Audio Processing ──────────────────────────────────────────────────────────

def apply_voice_effect(input_path: Path, output_path: Path, effect_chain: str) -> Path:
    """Apply FFmpeg audio filter chain to a segment."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", effect_chain,
        "-ar", "44100",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        import shutil
        shutil.copy(input_path, output_path)
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds via FFprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 3.0
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])
    return 3.0


# ── Video Frame Generation ────────────────────────────────────────────────────

def wrap_text(text: str, max_chars: int = 55) -> str:
    lines = textwrap.wrap(text, width=max_chars)
    return "\\n".join(lines)


def escape_ffmpeg_text(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\u2019")
    text = text.replace(":", "\\:")
    text = text.replace("%", "\\%")
    text = text.replace("\n", "\\n")
    return text


def genre_colors(bible: StoryBible) -> tuple[str, str]:
    genre = (bible.genre_model_name or bible.genre or "").lower()
    for key in GENRE_COLORS:
        if key in genre:
            return GENRE_COLORS[key]
    return GENRE_COLORS["default"]


def get_speaker_color(speaker: str, _bible: StoryBible, _accent: str) -> str:
    if speaker == "narrator":
        return "0xdddddd"
    char_colors = [
        "0xff9f43", "0x54a0ff", "0xff6b6b", "0x5f27cd",
        "0x00d2d3", "0xff9ff3", "0x48dbfb", "0xfeca57",
    ]
    idx = sum(ord(c) for c in speaker) % len(char_colors)
    return char_colors[idx]


def build_video_segment(
    audio_path: Path,
    output_path: Path,
    speaker: str,
    text: str,
    duration: float,
    bg_color: str,
    accent_color: str,
    speaker_color: str,
    story_title: str,
    chapter_num: int,
    font_path: str = "",
) -> Path:
    """Render one video segment: colored background + speaker name + dialogue text."""
    font_arg = f":fontfile={font_path}" if font_path and Path(font_path).exists() else ""
    wrapped = escape_ffmpeg_text(wrap_text(text, max_chars=52))
    speaker_display = escape_ffmpeg_text(speaker.upper())
    title_display = escape_ffmpeg_text(story_title[:40])

    name_y = "180"
    text_y = "260"

    vf_filters = [
        f"drawbox=x=0:y=0:w={VIDEO_W}:h=80:color={bg_color}@0.9:t=fill",
        f"drawbox=x=0:y={VIDEO_H-80}:w={VIDEO_W}:h=80:color={bg_color}@0.9:t=fill",
        f"drawbox=x=(iw-600)/2:y={int(name_y)+70}:w=600:h=3:color={accent_color}@0.9:t=fill",
        (
            f"drawtext=text='{speaker_display}'"
            f":fontsize=52:fontcolor={speaker_color}"
            f":x=(w-text_w)/2:y={name_y}"
            f":shadowcolor=black@0.8:shadowx=2:shadowy=2" + font_arg
        ),
        (
            f"drawtext=text='{wrapped}'"
            f":fontsize=36:fontcolor=0xeeeeee"
            f":x=(w-text_w)/2:y={text_y}"
            f":line_spacing=10"
            f":shadowcolor=black@0.7:shadowx=1:shadowy=1" + font_arg
        ),
        (
            f"drawtext=text='{title_display}  •  Chapter {chapter_num}'"
            f":fontsize=22:fontcolor=0x888888:x=40:y={VIDEO_H - 50}" + font_arg
        ),
    ]

    vf = ",".join(vf_filters)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:size={VIDEO_W}x{VIDEO_H}:rate={FPS}",
        "-i", str(audio_path),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr[-500:]}")
    return output_path


def build_title_card(
    output_path: Path,
    story_title: str,
    chapter_title: str,
    chapter_num: int,
    bg_color: str,
    accent_color: str,
    duration: float = 4.0,
    font_path: str = "",
) -> Path:
    font_arg = f":fontfile={font_path}" if font_path and Path(font_path).exists() else ""
    title_esc = escape_ffmpeg_text(story_title)
    chapter_esc = escape_ffmpeg_text(f"Chapter {chapter_num}: {chapter_title}")

    vf = ",".join([
        f"drawbox=x=(iw-400)/2:y=460:w=400:h=3:color={accent_color}@0.9:t=fill",
        (
            f"drawtext=text='{title_esc}':fontsize=72:fontcolor=0xffffff"
            f":x=(w-text_w)/2:y=380"
            f":shadowcolor=black@0.9:shadowx=3:shadowy=3" + font_arg
        ),
        (
            f"drawtext=text='{chapter_esc}':fontsize=40:fontcolor={accent_color}"
            f":x=(w-text_w)/2:y=490"
            f":shadowcolor=black@0.8:shadowx=2:shadowy=2" + font_arg
        ),
    ])

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:size={VIDEO_W}x{VIDEO_H}:rate={FPS}",
        "-f", "lavfi", "-i", "aevalsrc=0:c=stereo:s=44100",
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg title card error: {result.stderr[-500:]}")
    return output_path


# ── Full Chapter Video Pipeline ───────────────────────────────────────────────

def generate_chapter_video(
    bible: StoryBible,
    chapter_number: int,
    segments: list[Segment],
    segment_audio_files: list[Path],
    chapter_title: str = "",
    on_progress=None,
) -> Path:
    """
    Full pipeline:
      1. Apply voice effects to each segment audio
      2. Build video clip per segment
      3. Concatenate all clips
      4. Add fade in/out
    Returns path to final chapter video (.mp4).
    """
    bg_color, accent_color = genre_colors(bible)

    chapter_dir = OUTPUT_DIR / bible.story_id / f"chapter_{chapter_number:02d}_video"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    effected_clips = []

    # Step 1: Title card
    title_card_path = chapter_dir / "000_title.mp4"
    if on_progress:
        on_progress("Rendering title card...")
    build_title_card(
        title_card_path,
        story_title=bible.title,
        chapter_title=chapter_title,
        chapter_num=chapter_number,
        bg_color=bg_color,
        accent_color=accent_color,
    )
    effected_clips.append(title_card_path)

    # Step 2: Process each segment
    for i, (seg, raw_audio) in enumerate(zip(segments, segment_audio_files)):
        if not raw_audio.exists() or not seg.text.strip():
            continue

        if on_progress:
            on_progress(f"Segment {i+1}/{len(segments)}: [{seg.speaker}]")

        effect_chain  = detect_voice_effect(seg.speaker, bible)
        effected_audio = chapter_dir / f"{i:04d}_audio_{seg.speaker.lower().replace(' ', '_')}.mp3"
        apply_voice_effect(raw_audio, effected_audio, effect_chain)

        duration = get_audio_duration(effected_audio)
        duration = max(duration, 1.5)

        speaker_color = get_speaker_color(seg.speaker, bible, accent_color)

        clip_path = chapter_dir / f"{i:04d}_clip.mp4"
        build_video_segment(
            audio_path=effected_audio,
            output_path=clip_path,
            speaker=seg.speaker,
            text=seg.text,
            duration=duration,
            bg_color=bg_color,
            accent_color=accent_color,
            speaker_color=speaker_color,
            story_title=bible.title,
            chapter_num=chapter_number,
        )
        effected_clips.append(clip_path)

    if len(effected_clips) <= 1:
        raise RuntimeError("Not enough segments to build video.")

    # Step 3: Concatenate
    if on_progress:
        on_progress("Concatenating clips...")

    concat_list = chapter_dir / "concat.txt"
    with open(concat_list, "w") as f:
        for clip in effected_clips:
            f.write(f"file '{clip.resolve()}'\n")

    raw_output = chapter_dir / "raw_concat.mp4"
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-pix_fmt", "yuv420p",
        str(raw_output),
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Concat error: {result.stderr[-500:]}")

    # Step 4: Final encode with fades
    if on_progress:
        on_progress("Adding fade effects and finalizing...")

    final_output = OUTPUT_DIR / bible.story_id / f"chapter_{chapter_number:02d}.mp4"
    final_output.parent.mkdir(parents=True, exist_ok=True)

    total_duration = get_audio_duration(raw_output)
    fade_out_start = max(0, total_duration - 2.0)

    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_output),
        "-vf", f"fade=t=in:st=0:d=1.5,fade=t=out:st={fade_out_start:.2f}:d=2.0",
        "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start:.2f}:d=2.0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(final_output),
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Final encode error: {result.stderr[-500:]}")

    return final_output


def merge_chapter_videos(bible: StoryBible, chapter_numbers: list[int]) -> Path:
    """Merge multiple chapter videos into one full story video."""
    chapter_files = [
        OUTPUT_DIR / bible.story_id / f"chapter_{num:02d}.mp4"
        for num in chapter_numbers
        if (OUTPUT_DIR / bible.story_id / f"chapter_{num:02d}.mp4").exists()
    ]
    if not chapter_files:
        raise RuntimeError("No chapter videos found to merge.")

    concat_list = OUTPUT_DIR / bible.story_id / "full_concat.txt"
    with open(concat_list, "w") as f:
        for p in chapter_files:
            f.write(f"file '{p.resolve()}'\n")

    output = OUTPUT_DIR / bible.story_id / "full_story.mp4"
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(output),
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Merge error: {result.stderr[-500:]}")

    return output
