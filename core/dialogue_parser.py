"""
core/dialogue_parser.py — Splits story text into narrator + character dialogue segments.

Extended from v1 with:
- emotion_score: DeepSeek EmotionScore per segment
- ssml_pause_before_ms: SSML pause duration computed from emotion + position
- wpm_hint: suggested words-per-minute from emotion (for voice engine)

Research foundation:
- SSML pause timing: standard 500ms, emotional 1-3s, pre-climax 2-5s
- WPM by emotion: sad/serious 100-125, normal 140-160, excited/angry 160-200
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from core.story_bible import StoryBible
from core.emotion_scorer import EmotionScore


# ── SSML / WPM Constants ──────────────────────────────────────────────────────

# Words per minute by dominant emotion
EMOTION_WPM = {
    "sadness":      112,   # slow, heavy
    "fear":         130,   # tense but controlled
    "disgust":      120,   # low, deliberate
    "anger":        175,   # fast, clipped
    "joy":          165,   # quick, light
    "trust":        145,   # steady, warm
    "anticipation": 155,   # building pace
    "surprise":     170,   # burst, then pause
    "neutral":      150,   # default
}

# SSML break duration (ms) by dominant emotion and position context
SSML_PAUSE_DEFAULTS = {
    "sadness":      1500,   # long pause — grief breathes
    "fear":         800,    # short, held-breath pause
    "disgust":      600,
    "anger":        300,    # clipped, almost no pause
    "joy":          400,
    "trust":        600,
    "anticipation": 1200,   # let the dread build
    "surprise":     2000,   # pause AFTER the shock
    "neutral":      500,
}

PRE_CLIMAX_PAUSE_MS = 3000    # 3 seconds before major beat reveals
SENTENCE_END_PAUSE_MS = 500   # standard sentence-end pause
PARAGRAPH_PAUSE_MS = 800


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class Segment:
    speaker: str        # "narrator" or character name
    text: str

    # Voice assignment (filled by voice_engine)
    voice_id: str = ""

    # Emotion (filled by emotion_scorer, optional)
    emotion_score: Optional[EmotionScore] = None

    # SSML pause BEFORE this segment (ms) — 0 = no pause tag injected
    ssml_pause_before_ms: int = 0

    # Words per minute hint for this segment
    wpm_hint: int = 150

    # Position in chapter (0.0-1.0)
    position_in_chapter: float = 0.0


def wpm_for_emotion(emotion_score: Optional[EmotionScore]) -> int:
    """Return suggested WPM based on dominant emotion."""
    if not emotion_score or not emotion_score.dominant_emotion:
        return EMOTION_WPM["neutral"]
    return EMOTION_WPM.get(emotion_score.dominant_emotion, EMOTION_WPM["neutral"])


def ssml_pause_for_emotion(
    emotion_score: Optional[EmotionScore],
    position_in_chapter: float = 0.5,
    is_pre_climax: bool = False,
) -> int:
    """
    Return SSML break duration in ms for a segment.

    Args:
        emotion_score: DeepSeek emotion score for this segment
        position_in_chapter: 0.0-1.0 (late position = longer pauses)
        is_pre_climax: True if this segment precedes a major reveal/beat
    """
    if is_pre_climax:
        return PRE_CLIMAX_PAUSE_MS

    if not emotion_score or not emotion_score.dominant_emotion:
        return SENTENCE_END_PAUSE_MS

    base = SSML_PAUSE_DEFAULTS.get(emotion_score.dominant_emotion, SENTENCE_END_PAUSE_MS)

    # Intensity scaling: high intensity = longer pauses
    intensity_scale = 0.5 + emotion_score.intensity * 0.5
    result = int(base * intensity_scale)

    # Late chapter: stretch pauses (more dramatic)
    if position_in_chapter > 0.85:
        result = int(result * 1.4)
    elif position_in_chapter > 0.70:
        result = int(result * 1.2)

    # Clamp to reasonable range
    return max(300, min(4000, result))


# ── Parser ────────────────────────────────────────────────────────────────────

DIALOGUE_VERBS = (
    "said", "replied", "asked", "whispered", "shouted", "muttered", "cried",
    "exclaimed", "answered", "called", "added", "continued", "began", "noted",
    "announced", "declared", "insisted", "snapped", "growled", "breathed",
    "murmured", "laughed", "sighed", "hissed", "pleaded", "demanded",
    "admitted", "confessed", "warned", "reminded", "urged", "suggested",
)

_VERB_PATTERN = "|".join(DIALOGUE_VERBS)


def parse_story_into_segments(
    text: str,
    bible: StoryBible,
    score_emotions: bool = False,
) -> list[Segment]:
    """
    Split a chapter/text into narrator + character dialogue segments.

    Args:
        text: full chapter text
        bible: StoryBible for character name lookup
        score_emotions: if True and DEEPSEEK_API_KEY set, score each segment

    Returns:
        list[Segment]
    """
    segments: list[Segment] = []
    lines = text.split("\n")
    character_names = {c.name.lower(): c.name for c in bible.characters.values()}
    total_lines = max(1, len([l for l in lines if l.strip()]))
    line_idx = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue

        speaker, dialogue, narration = _extract_dialogue(line, character_names)
        position = line_idx / total_lines

        if narration:
            segments.append(Segment(
                speaker="narrator",
                text=narration,
                position_in_chapter=position,
            ))
        if dialogue and speaker:
            segments.append(Segment(
                speaker=speaker,
                text=dialogue,
                position_in_chapter=position,
            ))
        elif dialogue and not speaker:
            segments.append(Segment(
                speaker="narrator",
                text=f'"{dialogue}"',
                position_in_chapter=position,
            ))
        elif not dialogue and not narration and line:
            segments.append(Segment(
                speaker="narrator",
                text=line,
                position_in_chapter=position,
            ))

        line_idx += 1

    # Score emotions if requested
    if score_emotions:
        _add_emotion_scores(segments, bible)

    # Compute SSML pauses and WPM hints
    _add_ssml_metadata(segments)

    return segments


def _add_emotion_scores(segments: list[Segment], bible: StoryBible):
    """Score each segment with DeepSeek (expensive — use sparingly)."""
    try:
        from core.emotion_scorer import score_dialogue_turn, score_text
    except ImportError:
        return

    scene_context = f"Story: {bible.title}. Genre: {bible.genre}."

    for seg in segments:
        if not seg.text.strip():
            continue
        try:
            if seg.speaker == "narrator":
                seg.emotion_score = score_text(seg.text[:500], scene_context)
            else:
                seg.emotion_score = score_dialogue_turn(seg.speaker, seg.text[:500], scene_context)
        except Exception:
            pass


def _add_ssml_metadata(segments: list[Segment]):
    """Compute SSML pause and WPM for each segment based on emotion + position."""
    for i, seg in enumerate(segments):
        # Check if next segment is a climax beat (simple heuristic)
        is_pre_climax = False
        if i < len(segments) - 1:
            next_text = segments[i + 1].text.lower()
            climax_kws = ["shot rang", "suddenly", "everything changed", "revelation",
                          "at last", "finally understood", "the truth", "he killed",
                          "she killed", "explosion", "gunshot", "died"]
            is_pre_climax = any(k in next_text for k in climax_kws)

        seg.ssml_pause_before_ms = ssml_pause_for_emotion(
            seg.emotion_score,
            seg.position_in_chapter,
            is_pre_climax,
        )
        seg.wpm_hint = wpm_for_emotion(seg.emotion_score)


# ── Extraction ────────────────────────────────────────────────────────────────

def _extract_dialogue(line: str, character_names: dict) -> tuple[str, str, str]:
    """
    Returns (speaker_name, dialogue_text, narration_text).
    Any can be empty.
    """
    # Pattern 1: "dialogue," Name verb...
    match = re.search(
        r'^(.*?)"([^"]+)"[,.]?\s*'
        r'([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\s+'
        rf'({_VERB_PATTERN})(.*?)$',
        line,
    )
    if match:
        pre      = match.group(1).strip()
        dialogue = match.group(2).strip()
        speaker_cand = match.group(3).strip()
        post     = match.group(5).strip()
        speaker  = _match_character(speaker_cand, character_names)
        narration = " ".join(filter(None, [pre, post]))
        return speaker, dialogue, narration

    # Pattern 2: Name verb: "dialogue"
    match = re.search(
        rf'^([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\s+({_VERB_PATTERN}):\s*"([^"]+)"(.*)$',
        line,
    )
    if match:
        speaker_cand = match.group(1).strip()
        dialogue     = match.group(3).strip()
        post         = match.group(4).strip()
        speaker      = _match_character(speaker_cand, character_names)
        return speaker, dialogue, post

    # Pattern 3: "dialogue" — Name
    match = re.search(
        r'"([^"]+)"\s*[—–-]\s*([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)',
        line,
    )
    if match:
        dialogue     = match.group(1).strip()
        speaker_cand = match.group(2).strip()
        speaker      = _match_character(speaker_cand, character_names)
        return speaker, dialogue, ""

    # No dialogue — whole line is narration
    return "", "", line


def _match_character(name: str, character_names: dict) -> str:
    lower = name.lower()
    if lower in character_names:
        return character_names[lower]
    for key, canonical in character_names.items():
        if lower in key or key in lower:
            return canonical
    return name   # Unknown character — return as-is


# ── Utilities ─────────────────────────────────────────────────────────────────

def segments_summary(segments: list[Segment]) -> str:
    lines = []
    for i, seg in enumerate(segments):
        preview = seg.text[:60] + "..." if len(seg.text) > 60 else seg.text
        emotion_str = ""
        if seg.emotion_score:
            emotion_str = f" [{seg.emotion_score.dominant_emotion} {seg.emotion_score.intensity:.0%}]"
        lines.append(
            f"[{i:03d}] {seg.speaker.upper():<20} {preview}{emotion_str}"
        )
    return "\n".join(lines)


def inject_ssml_into_text(segments: list[Segment]) -> str:
    """
    Combine segments into a single SSML string suitable for TTS engines
    that support SSML (ElevenLabs v3 alpha).

    Standard use: each speaker's text is passed individually, not combined.
    This is for batch SSML generation if needed.
    """
    parts = []
    for seg in segments:
        if seg.ssml_pause_before_ms > 0:
            parts.append(f'<break time="{seg.ssml_pause_before_ms}ms"/>')
        parts.append(seg.text)
    return " ".join(parts)
