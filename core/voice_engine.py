"""
core/voice_engine.py — ElevenLabs TTS integration.

Extended from v1 with:
- emotion_to_wpm(): maps dominant emotion to speech rate
- wpm_to_stability(): maps WPM to ElevenLabs stability setting
- inject_ssml_pauses(): adds SSML break tags to text
- list_voices_for_language(): filter voices by language
- Emotion-driven stability/similarity settings per segment

Research foundation:
- WPM by emotion: sad/serious 100-125, normal 140-160, excited/angry 160-200
- ElevenLabs stability 0.0-1.0: low = more expressive/emotional, high = consistent
- ElevenLabs similarity_boost: 0.75-0.90 for character consistency
"""

import os
import re
from pathlib import Path
from typing import Optional

from core.story_bible import StoryBible, CharacterProfile
from core.dialogue_parser import Segment, EMOTION_WPM, SSML_PAUSE_DEFAULTS
from core.env import require_key


AUDIO_DIR  = Path(__file__).parent.parent / "audio"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ElevenLabs model — v2 is stable + high quality + multilingual
ELEVENLABS_MODEL = "eleven_multilingual_v2"
# For v3 alpha (better emotion control, requires access): "eleven_v3"

# ElevenLabs stability ranges by emotion intensity
# Low stability = more expressive delivery (good for high-emotion scenes)
# High stability = consistent tone (good for narrator)
EMOTION_STABILITY = {
    "anger":        0.30,   # very expressive
    "fear":         0.35,
    "sadness":      0.40,   # emotional but controlled
    "surprise":     0.35,
    "disgust":      0.38,
    "joy":          0.45,
    "anticipation": 0.50,
    "trust":        0.55,
    "neutral":      0.55,
    "narrator":     0.60,   # narrator: consistent
}

NARRATOR_STABILITY   = 0.60
NARRATOR_SIMILARITY  = 0.80
CHARACTER_SIMILARITY = 0.82


# ── Emotion → Voice Settings ──────────────────────────────────────────────────

def emotion_to_wpm(dominant_emotion: str) -> int:
    """Return WPM from dominant emotion name."""
    return EMOTION_WPM.get(dominant_emotion, EMOTION_WPM["neutral"])


def wpm_to_stability(wpm: int, is_narrator: bool = False) -> float:
    """
    Convert WPM hint to ElevenLabs stability.
    Lower WPM (sad, slow) = slightly higher stability (controlled delivery).
    Higher WPM (angry, fast) = lower stability (more expressive).
    """
    if is_narrator:
        return NARRATOR_STABILITY

    # Fast speech (anger/joy) → low stability (expressive)
    # Slow speech (sadness) → moderate stability (controlled emotional)
    if wpm >= 170:
        return 0.30
    elif wpm >= 155:
        return 0.38
    elif wpm >= 140:
        return 0.45
    elif wpm >= 125:
        return 0.50
    else:
        return 0.55


def stability_for_segment(seg: Segment) -> float:
    """Get stability for a segment from its emotion score."""
    if seg.speaker == "narrator":
        return NARRATOR_STABILITY
    if seg.emotion_score and seg.emotion_score.dominant_emotion:
        return EMOTION_STABILITY.get(seg.emotion_score.dominant_emotion, 0.45)
    return 0.45


def inject_ssml_pauses(text: str, pause_ms: int) -> str:
    """
    Prepend SSML break tag to text.
    Only used with ElevenLabs v3 (SSML support). For v2, pauses are handled
    by silence segments inserted between audio clips.
    """
    if pause_ms <= 0:
        return text
    return f'<break time="{pause_ms}ms"/>{text}'


def list_voices_for_language(language_code: str = "en") -> list[dict]:
    """
    Filter ElevenLabs voices by language support.
    eleven_multilingual_v2 supports 29 languages; this filters by fine-tuned voices.
    """
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=require_key("ELEVENLABS_API_KEY"))
        response = client.voices.get_all()
        voices = []
        for v in response.voices:
            labels = getattr(v, "labels", {}) or {}
            # Check language label
            voice_lang = labels.get("language", "en").lower()
            if language_code.lower() in voice_lang or language_code.lower() == "en":
                voices.append({
                    "voice_id":  v.voice_id,
                    "name":      v.name,
                    "category":  getattr(v, "category", ""),
                    "labels":    labels,
                    "language":  voice_lang,
                })
        return voices
    except Exception as e:
        print(f"  [voice_engine] Could not fetch voices: {e}")
        return []


# ── Client ────────────────────────────────────────────────────────────────────

def _client():
    from elevenlabs import ElevenLabs
    return ElevenLabs(api_key=require_key("ELEVENLABS_API_KEY"))


# ── Core TTS ──────────────────────────────────────────────────────────────────

def list_voices() -> list[dict]:
    """Return all available voices from ElevenLabs account."""
    client = _client()
    response = client.voices.get_all()
    return [
        {
            "voice_id": v.voice_id,
            "name":     v.name,
            "category": getattr(v, "category", ""),
            "labels":   getattr(v, "labels", {}),
        }
        for v in response.voices
    ]


def assign_voice_to_character(bible: StoryBible, character_name: str, voice_id: str, voice_name: str):
    """Assign an ElevenLabs voice to a character and save."""
    char = bible.get_character(character_name)
    if not char:
        raise ValueError(f"Character '{character_name}' not found in story bible.")
    char.voice_id   = voice_id
    char.voice_name = voice_name
    bible.save()


def assign_narrator_voice(bible: StoryBible, voice_id: str, voice_name: str):
    """Assign voice for the narrator."""
    bible.narrator_voice_id   = voice_id
    bible.narrator_voice_name = voice_name
    bible.save()


def text_to_speech(
    text: str,
    voice_id: str,
    output_path: Path,
    stability: float = 0.50,
    similarity: float = 0.80,
) -> Path:
    """Convert text to speech using ElevenLabs."""
    from elevenlabs import VoiceSettings
    client = _client()

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=ELEVENLABS_MODEL,
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity,
            style=0.4,
            use_speaker_boost=True,
        ),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return output_path


def _get_voice_for_segment(seg: Segment, bible: StoryBible) -> Optional[str]:
    """Get the ElevenLabs voice ID for a segment's speaker."""
    if seg.speaker == "narrator":
        return bible.narrator_voice_id or None

    char = bible.get_character(seg.speaker)
    if char and char.voice_id:
        return char.voice_id

    # Fallback to narrator voice
    return bible.narrator_voice_id or None


# ── Chapter Audio Generation ──────────────────────────────────────────────────

def generate_chapter_audio(
    bible: StoryBible,
    chapter_number: int,
    segments: list[Segment],
    return_segment_files: bool = False,
) -> "Path | tuple[Path, list[Path], list[Segment]]":
    """
    Generate audio for each segment with the correct character voice,
    then merge into one chapter audio file.

    Emotion-driven: each segment gets its own stability/similarity
    based on the segment's DeepSeek emotion score.

    If return_segment_files=True, also returns individual segment files
    (used by video_engine to apply per-segment voice effects).
    """
    story_audio_dir = AUDIO_DIR / bible.story_id / f"chapter_{chapter_number:02d}"
    story_audio_dir.mkdir(parents=True, exist_ok=True)

    segment_files  = []
    valid_segments = []

    for i, seg in enumerate(segments):
        if not seg.text.strip():
            continue

        voice_id = _get_voice_for_segment(seg, bible)
        if not voice_id:
            print(f"  [!] No voice for '{seg.speaker}' — skipping segment {i}")
            continue

        # Emotion-driven settings
        stability  = stability_for_segment(seg)
        similarity = NARRATOR_SIMILARITY if seg.speaker == "narrator" else CHARACTER_SIMILARITY

        # SSML pause: insert silence clip BEFORE segment
        if seg.ssml_pause_before_ms > 0:
            silence_path = story_audio_dir / f"seg_{i:04d}_silence.mp3"
            _generate_silence(seg.ssml_pause_before_ms, silence_path)
            segment_files.append(silence_path)

        seg_path = story_audio_dir / f"seg_{i:04d}_{seg.speaker.lower().replace(' ', '_')}.mp3"
        emotion_tag = ""
        if seg.emotion_score:
            emotion_tag = f" [{seg.emotion_score.dominant_emotion} {seg.emotion_score.intensity:.0%}]"
        print(f"  [{seg.speaker}]{emotion_tag}: {seg.text[:50]}...")

        try:
            text_to_speech(seg.text, voice_id, seg_path, stability, similarity)
            segment_files.append(seg_path)
            valid_segments.append(seg)
        except Exception as e:
            print(f"  [!] Audio error segment {i}: {e}")

    if not segment_files:
        raise RuntimeError("No audio segments were generated.")

    output_path = OUTPUT_DIR / bible.story_id / f"chapter_{chapter_number:02d}.mp3"
    merge_audio_files(segment_files, output_path)

    if return_segment_files:
        return output_path, segment_files, valid_segments
    return output_path


def _generate_silence(duration_ms: int, output_path: Path):
    """Generate a silent MP3 clip of given duration using pydub."""
    try:
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=duration_ms)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        silence.export(str(output_path), format="mp3")
    except ImportError:
        pass   # silently skip if pydub not available


def merge_audio_files(segment_files: list[Path], output_path: Path):
    """Merge multiple MP3 files into one using pydub."""
    try:
        from pydub import AudioSegment

        combined = AudioSegment.empty()
        standard_pause = AudioSegment.silent(duration=400)   # 400ms between segments

        for f in segment_files:
            try:
                seg_audio = AudioSegment.from_mp3(str(f))
                combined += seg_audio + standard_pause
            except Exception as e:
                print(f"  [!] Could not merge {f.name}: {e}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.export(str(output_path), format="mp3")
        print(f"\n  Merged audio saved: {output_path}")

    except ImportError:
        print("  [!] pydub not available — saving first segment only.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as out:
            for f in segment_files:
                out.write(f.read_bytes())


def preview_voice(
    voice_id: str,
    text: str = "Hello, I am your story character. Let me tell you a tale.",
) -> Path:
    """Generate a short voice preview."""
    preview_path = AUDIO_DIR / "previews" / f"{voice_id}_preview.mp3"
    return text_to_speech(text, voice_id, preview_path)
