"""
emotion_scorer.py — DeepSeek-V3 Plutchik emotion analysis.

Research foundation:
- Plutchik's Wheel of 8 Emotions (joy, trust, fear, surprise, sadness, disgust, anger, anticipation)
- VAD: Valence / Arousal / Dominance continuous dimensions (-1.0 to +1.0)
- DeepSeek-V3 accuracy: 74.94% overall, 95% fear recall, 94% joy recall
- Weak: surprise detection (37% recall) — not used as primary gate

API: DeepSeek is OpenAI-compatible. Uses openai SDK with custom base_url.
Fallback: if DEEPSEEK_API_KEY not set, returns neutral EmotionScore without crashing.
"""

import os
import json
import re
from dataclasses import dataclass, asdict, field


DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

PLUTCHIK_EMOTIONS = ["joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation"]


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class EmotionScore:
    # Plutchik 8 emotions (0.0 to 1.0 = percentage)
    joy:          float = 0.0
    trust:        float = 0.0
    fear:         float = 0.0
    surprise:     float = 0.0
    sadness:      float = 0.0
    disgust:      float = 0.0
    anger:        float = 0.0
    anticipation: float = 0.0

    # VAD continuous scores (-1.0 to +1.0)
    valence:    float = 0.0   # negative = unpleasant, positive = pleasant
    arousal:    float = 0.0   # negative = calm, positive = excited/intense
    dominance:  float = 0.0   # negative = submissive, positive = in control

    # Derived
    intensity:         float = 0.0   # composite 0.0-1.0 (max of 8 emotions)
    dominant_emotion:  str   = ""    # name of highest-scoring emotion

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionScore":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def plutchik_vector(self) -> list[float]:
        return [self.joy, self.trust, self.fear, self.surprise,
                self.sadness, self.disgust, self.anger, self.anticipation]

    def as_percentages(self) -> dict:
        return {e: round(getattr(self, e) * 100, 1) for e in PLUTCHIK_EMOTIONS}


def _neutral() -> EmotionScore:
    """Return a neutral EmotionScore (used as fallback when API unavailable)."""
    return EmotionScore(
        joy=0.3, trust=0.3, fear=0.1, surprise=0.1,
        sadness=0.1, disgust=0.05, anger=0.05, anticipation=0.2,
        valence=0.1, arousal=0.0, dominance=0.0,
        intensity=0.3, dominant_emotion="joy"
    )


def _derive_fields(score: EmotionScore) -> EmotionScore:
    """Compute intensity and dominant_emotion from raw scores."""
    values = {e: getattr(score, e) for e in PLUTCHIK_EMOTIONS}
    score.intensity = max(values.values())
    score.dominant_emotion = max(values, key=values.get)
    return score


# ── DeepSeek Client ───────────────────────────────────────────────────────────

def _client():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def _parse_emotion_json(raw: str) -> dict | None:
    """Extract JSON from DeepSeek response, handle markdown code fences."""
    raw = raw.strip()
    # Strip ```json ... ``` fences
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        # Try to find first {...} block
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


EMOTION_PROMPT_TEMPLATE = """Analyze the emotional content of this text.
{context_line}
Text: "{text}"

Return ONLY valid JSON with these exact fields (all floats 0.0-1.0 for emotions, -1.0 to +1.0 for VAD):
{{
  "joy": 0.0,
  "trust": 0.0,
  "fear": 0.0,
  "surprise": 0.0,
  "sadness": 0.0,
  "disgust": 0.0,
  "anger": 0.0,
  "anticipation": 0.0,
  "valence": 0.0,
  "arousal": 0.0,
  "dominance": 0.0
}}
No explanations. Only JSON."""


# ── Public API ────────────────────────────────────────────────────────────────

def score_text(text: str, context: str = "") -> EmotionScore:
    """
    Analyze text and return Plutchik emotion scores + VAD.

    Args:
        text: dialogue or prose to analyze
        context: optional scene context for accuracy

    Returns:
        EmotionScore with 8 Plutchik emotions (0-1) + VAD (-1 to +1)

    Example:
        score_text("I trusted you and you betrayed me")
        → EmotionScore(sadness=0.82, anger=0.71, disgust=0.55, ..., dominant_emotion="sadness")
    """
    client = _client()
    if client is None:
        return _neutral()

    context_line = f"Scene context: {context}" if context else ""
    prompt = EMOTION_PROMPT_TEMPLATE.format(
        context_line=context_line,
        text=text[:1000],  # cap at 1000 chars
    )

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        raw = response.choices[0].message.content
        data = _parse_emotion_json(raw)
        if not data:
            return _neutral()

        score = EmotionScore(
            joy=          float(data.get("joy", 0.0)),
            trust=        float(data.get("trust", 0.0)),
            fear=         float(data.get("fear", 0.0)),
            surprise=     float(data.get("surprise", 0.0)),
            sadness=      float(data.get("sadness", 0.0)),
            disgust=      float(data.get("disgust", 0.0)),
            anger=        float(data.get("anger", 0.0)),
            anticipation= float(data.get("anticipation", 0.0)),
            valence=      float(data.get("valence", 0.0)),
            arousal=      float(data.get("arousal", 0.0)),
            dominance=    float(data.get("dominance", 0.0)),
        )
        return _derive_fields(score)

    except Exception as e:
        print(f"  [emotion_scorer] DeepSeek error: {e}")
        return _neutral()


def score_dialogue_turn(speaker: str, text: str, scene_context: str = "") -> EmotionScore:
    """
    Score a single dialogue line from a specific character.

    Args:
        speaker: character name
        text: the dialogue line
        scene_context: what's happening in the scene

    Returns:
        EmotionScore
    """
    context = f"{speaker} is speaking. {scene_context}" if scene_context else f"{speaker} is speaking."
    return score_text(text, context)


def score_chapter(chapter_text: str, sections: int = 5) -> dict:
    """
    Score a full chapter by splitting into sections.

    Args:
        chapter_text: full chapter prose
        sections: how many sections to split into (default 5)

    Returns:
        {
            "overall": EmotionScore,
            "sections": [{"section": int, "preview": str, "score": EmotionScore}],
            "arc_shape": "rising"|"falling"|"flat"|"valley"|"peak"|"unknown"
        }
    """
    client = _client()

    # Split chapter into sections
    words = chapter_text.split()
    section_size = max(1, len(words) // sections)
    section_texts = []
    for i in range(sections):
        start = i * section_size
        end = start + section_size if i < sections - 1 else len(words)
        section_texts.append(" ".join(words[start:end]))

    section_scores = []
    for i, section_text in enumerate(section_texts):
        score = score_text(section_text[:800])
        section_scores.append({
            "section": i + 1,
            "preview": section_text[:60] + "...",
            "score": score,
        })

    # Overall score from full text (first 1000 words)
    overall_preview = " ".join(words[:1000])
    overall = score_text(overall_preview)

    # Determine arc shape from intensity across sections
    intensities = [s["score"].intensity for s in section_scores]
    arc_shape = _classify_arc_shape(intensities)

    return {
        "overall": overall,
        "sections": section_scores,
        "arc_shape": arc_shape,
    }


def _classify_arc_shape(intensities: list[float]) -> str:
    if len(intensities) < 2:
        return "unknown"
    first_half_avg = sum(intensities[:len(intensities)//2]) / (len(intensities)//2)
    second_half_avg = sum(intensities[len(intensities)//2:]) / (len(intensities) - len(intensities)//2)
    mid = intensities[len(intensities)//2]
    first = intensities[0]
    last = intensities[-1]
    peak = max(intensities)
    trough = min(intensities)

    if last - first > 0.2:
        return "rising"
    elif first - last > 0.2:
        return "falling"
    elif mid < first - 0.15 and mid < last - 0.15:
        return "valley"
    elif peak > first + 0.15 and peak > last + 0.15:
        return "peak"
    else:
        return "flat"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two emotion vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x ** 2 for x in a) ** 0.5
    mag_b = sum(x ** 2 for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def emotion_consistency(actual: EmotionScore, target_emotions: dict) -> float:
    """
    Compare actual emotion score against target emotion dict.
    Returns 0.0-1.0 (1.0 = perfect match).

    Args:
        actual: EmotionScore from score_text()
        target_emotions: dict like {"fear": 0.7, "anticipation": 0.8}

    Returns:
        float: consistency score 0.0-1.0
    """
    if not target_emotions:
        return 0.8  # no target = assume OK

    target_vec = [target_emotions.get(e, 0.0) for e in PLUTCHIK_EMOTIONS]
    actual_vec = actual.plutchik_vector()
    return round(cosine_similarity(actual_vec, target_vec), 3)
