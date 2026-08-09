"""
interest_scorer.py — Scene Interest Score (SIS 0-100).

Research foundation:
- Brewer & Lichtenstein (1982): Suspense formula r=0.8234
  Suspense = (Imminence × Importance × Foregroundedness) / (1 + Confidence)
- Loewenstein (1994): Information Gap Theory — curiosity peaks at 30-70% info revealed
- Genette (1980): Narrative Modes — Scene, Summary, Stretch, Ellipsis, Pause
- Dwight Swain: Scene & Sequel — action/reaction pacing ratio
- Anti-monotony rule: no 2+ consecutive high-SIS or low-SIS scenes

SIS bands → word count allocation:
  SIS ≥ 85  → 3,000-5,000 words, Stretch mode (slow, immersive)
  SIS 70-84 → 2,000-3,000 words, Scene mode
  SIS 50-69 → 1,500-2,000 words, Scene mode
  SIS 30-49 → 800-1,500 words, Summary mode
  SIS < 30  → 200-800 words, Ellipsis/skip
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from core.arc_calculator import STC_BEAT_WEIGHTS, STC_BEAT_POSITIONS, normalize_beats_covered, normalize_beat_name


# ── Suspense Formula Constants (Brewer & Lichtenstein) ────────────────────────

SUSPENSE_BASE_WEIGHTS = {
    # Genre-tuned in genre models, these are story-agnostic defaults
    "imminence":          0.35,    # How close is the threat/event?
    "importance":         0.30,    # Life/death stakes?
    "foregroundedness":   0.25,    # Is the threat front-of-mind?
    "confidence":         0.10,    # Uncertainty multiplier (lower = more suspense)
}

# ── Narrative Mode Definitions (Genette) ─────────────────────────────────────

NARRATIVE_MODES = {
    "Stretch":   "Narrated time > Story time — slow, immersive, every moment expanded",
    "Scene":     "Narrated time ≈ Story time — real-time dialogue/action",
    "Summary":   "Narrated time < Story time — days/weeks compressed",
    "Ellipsis":  "Story time skipped entirely — 'three weeks later'",
    "Pause":     "Story time frozen — description, backstory, reflection only",
}

# ── SIS Band → Word Count Targets ────────────────────────────────────────────

SIS_WORD_COUNT_BANDS = [
    (85, 100, 3000, 5000, "Stretch"),
    (70,  84, 2000, 3000, "Scene"),
    (50,  69, 1500, 2000, "Scene"),
    (30,  49,  800, 1500, "Summary"),
    ( 0,  29,  200,  800, "Ellipsis"),
]

# ── Anti-Monotony Constants ───────────────────────────────────────────────────

MAX_CONSECUTIVE_HIGH = 2     # max scenes ≥ 80 SIS in a row
MAX_CONSECUTIVE_LOW  = 2     # max scenes ≤ 35 SIS in a row
HIGH_THRESHOLD       = 80
LOW_THRESHOLD        = 35


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class SceneInterestScore:
    # Component scores (0-100 each)
    beat_weight:          float = 50.0    # STC beat importance at this position
    suspense_score:       float = 50.0    # Brewer & Lichtenstein formula output
    info_gap_score:       float = 50.0    # Loewenstein — mystery/curiosity density
    emotional_contrast:   float = 50.0    # how different emotion is from prev scene
    hook_strength:        float = 50.0    # ending hook / cliffhanger potential
    surprise_potential:   float = 50.0    # unexpected reversal or reveal

    # Anti-monotony penalty (-20 to 0)
    monotony_penalty:     float = 0.0

    # Final computed score
    sis_total:            float = 50.0    # 0-100

    # Output allocation
    word_count_min:       int   = 800
    word_count_max:       int   = 1500
    word_count_target:    int   = 1150
    narrative_mode:       str   = "Summary"
    scene_type:           str   = "action"    # action / reflection / transition

    # Debug
    beat_name:            str   = ""
    position_pct:         float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (
            f"SIS={self.sis_total:.0f} | {self.narrative_mode} | "
            f"{self.word_count_target:,} words | beat={self.beat_name or 'none'} | "
            f"suspense={self.suspense_score:.0f} info_gap={self.info_gap_score:.0f} "
            f"contrast={self.emotional_contrast:.0f} hook={self.hook_strength:.0f}"
        )


# ── Component Scorers ─────────────────────────────────────────────────────────

def _score_beat_weight(position_pct: float, beats_covered: list[str]) -> tuple[float, str]:
    """
    Returns (score 0-100, beat_name).
    Uses STC beat weights. If no beat assigned, interpolates from position.
    """
    if beats_covered:
        normalized = normalize_beats_covered(beats_covered)
        best_beat = max(normalized, key=lambda b: STC_BEAT_WEIGHTS.get(b, 50))
        weight = STC_BEAT_WEIGHTS.get(best_beat, 50)
        return float(weight), best_beat

    # Interpolate from position — find nearest beat
    closest_name = "default"
    closest_dist = 1.0
    for name, (pos, _intensity) in STC_BEAT_POSITIONS.items():
        dist = abs(position_pct - pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_name = name

    # Weight decays with distance from beat
    raw_weight = STC_BEAT_WEIGHTS.get(closest_name, 50)
    decay = max(0.5, 1.0 - closest_dist * 3.0)   # within 33% still counts
    return round(float(raw_weight) * decay, 1), closest_name


def _score_suspense(
    scene_draft: str,
    imminence: float = 0.5,
    importance: float = 0.5,
    foregroundedness: float = 0.5,
    confidence: float = 0.5,
) -> float:
    """
    Brewer & Lichtenstein formula: S = (I × Im × F) / (1 + C)
    Returns 0-100.

    When scene_draft is available, we infer these values from keywords.
    All inputs are 0.0-1.0.
    """
    # If given explicit values, compute directly
    if scene_draft:
        text_lower = scene_draft.lower()

        # Imminence signals
        imminence_kws = ["now", "suddenly", "immediately", "right now", "about to", "any moment",
                         "seconds", "runs", "burst", "shoots", "stabs", "fires", "rushes"]
        imminence = min(1.0, 0.3 + 0.07 * sum(1 for k in imminence_kws if k in text_lower))

        # Importance signals
        importance_kws = ["kill", "die", "dead", "death", "murder", "destroyed", "explosion",
                          "life", "lives", "lose everything", "only chance", "forever",
                          "never", "last", "end", "destroyed", "loved one", "family"]
        importance = min(1.0, 0.3 + 0.08 * sum(1 for k in importance_kws if k in text_lower))

        # Foregroundedness (is threat in focus?)
        fg_kws = ["he knew", "she knew", "they knew", "danger", "threat", "risk",
                  "warned", "afraid", "scared", "terrified", "heart pounded", "fear"]
        foregroundedness = min(1.0, 0.3 + 0.1 * sum(1 for k in fg_kws if k in text_lower))

        # Confidence that outcome will be bad (high = less suspense)
        certainty_kws = ["obviously", "clearly", "of course", "certainly", "definitely",
                         "knew it would", "no doubt"]
        confidence = min(0.9, 0.2 + 0.15 * sum(1 for k in certainty_kws if k in text_lower))

    raw = (imminence * importance * foregroundedness) / (1.0 + confidence)
    # raw is 0-1, scale to 0-100
    return round(min(100.0, raw * 200.0), 1)


def _score_info_gap(scene_draft: str, position_pct: float) -> float:
    """
    Loewenstein (1994): curiosity peaks at 30-70% info revealed.
    Optimal: tease but don't resolve.
    Returns 0-100.
    """
    # Position-based base (peaks at 30-70% story position)
    if 0.30 <= position_pct <= 0.70:
        position_bonus = 20.0
    elif 0.15 <= position_pct <= 0.85:
        position_bonus = 10.0
    else:
        position_bonus = 0.0

    score = 40.0 + position_bonus

    if scene_draft:
        text_lower = scene_draft.lower()
        # Information gap openers
        gap_kws = ["?", "who", "why", "how", "what", "secret", "hidden", "mystery",
                   "strange", "odd", "unusual", "couldn't understand", "didn't know why",
                   "hadn't told", "kept from", "revealed", "discovered", "realized"]
        gap_count = sum(1 for k in gap_kws if k in text_lower)

        # Payoff keywords (too many = gap closed = less curiosity)
        payoff_kws = ["finally", "at last", "the truth was", "it was", "turned out",
                      "explained", "because", "understood now", "now he knew"]
        payoff_count = sum(1 for k in payoff_kws if k in text_lower)

        score += min(30.0, gap_count * 3.0)
        score -= min(20.0, payoff_count * 4.0)

    return round(max(0.0, min(100.0, score)), 1)


def _score_emotional_contrast(
    current_emotions: dict,
    previous_scores: list["SceneInterestScore"],
) -> float:
    """
    Contrast between this scene's target emotion and the previous scene.
    High contrast = reader stays engaged (emotional reset).
    Returns 0-100.
    """
    if not previous_scores or not current_emotions:
        return 50.0

    # Use a simple heuristic: did the dominant emotion type change?
    prev_beat = previous_scores[-1].beat_name
    curr_dominant = max(current_emotions, key=current_emotions.get) if current_emotions else ""

    # Polarity flip: positive → negative or vice versa
    positive_emotions = {"joy", "trust", "anticipation"}
    negative_emotions = {"fear", "sadness", "disgust", "anger"}

    if curr_dominant in positive_emotions and prev_beat in (
        "All Is Lost", "Dark Night", "Dark Night of Soul", "Bad Guys Close In"
    ):
        return 85.0   # contrast after dark moment
    if curr_dominant in negative_emotions and prev_beat in ("Fun and Games", "B Story"):
        return 80.0   # tension after lightness

    # Default moderate contrast
    contrast = 50.0
    if len(previous_scores) >= 2:
        prev_sis = previous_scores[-1].sis_total
        prev_prev_sis = previous_scores[-2].sis_total
        if abs(prev_sis - prev_prev_sis) < 10:
            contrast = 30.0   # flat sequence — this scene should contrast
        else:
            contrast = 60.0

    return round(contrast, 1)


def _score_hook_strength(scene_draft: str, position_pct: float) -> float:
    """
    How strong is the scene-ending hook / cliffhanger?
    Returns 0-100.
    """
    score = 40.0

    # Late in story = cliffhanger expectation higher
    if position_pct > 0.80:
        score += 20.0
    elif position_pct > 0.60:
        score += 10.0

    if scene_draft:
        text_lower = scene_draft.lower()
        # Hook signals in last 20% of scene draft
        end_section = text_lower[-len(text_lower) // 5:]
        hook_kws = ["suddenly", "then", "but", "except", "however", "wait",
                    "wrong", "mistake", "realised", "realized", "phone rang",
                    "door opened", "shot rang", "everything changed",
                    "she didn't know", "he didn't know", "no one knew"]
        hook_count = sum(1 for k in hook_kws if k in end_section)
        score += min(30.0, hook_count * 10.0)

        # Question ending = hook
        if end_section.strip().endswith("?"):
            score += 15.0

    return round(min(100.0, score), 1)


def _score_surprise_potential(
    scene_draft: str,
    beats_covered: list[str],
    position_pct: float,
) -> float:
    """
    Potential for reversal or unexpected revelation.
    Returns 0-100.
    """
    score = 35.0

    # High-surprise beats
    surprise_beats = {"Catalyst", "Midpoint", "All Is Lost", "Break into Three", "Finale"}
    if any(b in surprise_beats for b in beats_covered):
        score += 35.0

    # Late-story reveals are more impactful
    if 0.70 <= position_pct <= 0.90:
        score += 15.0

    if scene_draft:
        text_lower = scene_draft.lower()
        reversal_kws = ["didn't expect", "surprised", "shocked", "twist",
                        "reveal", "finally", "turned out", "lied",
                        "betrayed", "never knew", "all along"]
        score += min(20.0, sum(1 for k in reversal_kws if k in text_lower) * 5.0)

    return round(min(100.0, score), 1)


def _monotony_penalty(
    current_sis_estimate: float,
    previous_scores: list["SceneInterestScore"],
) -> float:
    """
    Anti-monotony: penalize if too many consecutive high or low scenes.
    Returns negative value (0 to -20).
    """
    if len(previous_scores) < 2:
        return 0.0

    recent = [s.sis_total for s in previous_scores[-2:]]

    # Consecutive highs
    if all(s >= HIGH_THRESHOLD for s in recent) and current_sis_estimate >= HIGH_THRESHOLD:
        return -20.0

    # Consecutive lows
    if all(s <= LOW_THRESHOLD for s in recent) and current_sis_estimate <= LOW_THRESHOLD:
        return -15.0   # nudge up a bit — reader can't stay in low for too long

    return 0.0


def _compute_sis_total(sis: "SceneInterestScore") -> float:
    """
    Weighted combination of all component scores.
    Weights tuned to give beat position highest leverage.
    """
    weighted = (
        sis.beat_weight        * 0.25 +
        sis.suspense_score     * 0.25 +
        sis.info_gap_score     * 0.15 +
        sis.emotional_contrast * 0.15 +
        sis.hook_strength      * 0.10 +
        sis.surprise_potential * 0.10
    )
    total = weighted + sis.monotony_penalty
    return round(max(0.0, min(100.0, total)), 1)


def _allocate_words(sis_total: float) -> tuple[int, int, int, str]:
    """Returns (min_words, max_words, target_words, narrative_mode)."""
    for lo, hi, wmin, wmax, mode in SIS_WORD_COUNT_BANDS:
        if lo <= sis_total <= hi:
            target = (wmin + wmax) // 2
            return wmin, wmax, target, mode
    return 200, 800, 500, "Ellipsis"


def _infer_scene_type(beats_covered: list[str], position_pct: float) -> str:
    """Classify scene as action / reflection / transition."""
    reflection_beats = {
        "Debate", "B Story", "Dark Night of Soul", "Dark Night", "Final Image",
    }
    transition_beats = {"Break into Two", "Break into Three"}

    if any(b in reflection_beats for b in beats_covered):
        return "reflection"
    if any(b in transition_beats for b in beats_covered):
        return "transition"
    if position_pct < 0.08 or position_pct > 0.95:
        return "reflection"
    return "action"


# ── Public API ────────────────────────────────────────────────────────────────

def score_scene(
    scene_draft: str,
    beats_covered: list[str],
    position_pct: float,
    previous_scores: list[SceneInterestScore] = None,
    target_emotions: dict = None,
) -> SceneInterestScore:
    """
    Compute Scene Interest Score for a scene.

    Args:
        scene_draft: brief description or draft text of the scene
        beats_covered: list of STC beat names this scene covers (e.g. ["All Is Lost"])
        position_pct: 0.0-1.0 position in story (chapter_number / total_chapters)
        previous_scores: list of previous SceneInterestScore objects (for anti-monotony)
        target_emotions: dict like {"fear": 0.7, "anticipation": 0.8} for this scene

    Returns:
        SceneInterestScore with all components + word count allocation
    """
    previous_scores = previous_scores or []
    beats_covered = normalize_beats_covered(beats_covered or [])

    sis = SceneInterestScore(position_pct=position_pct)

    # Score each component
    sis.beat_weight, sis.beat_name = _score_beat_weight(position_pct, beats_covered)
    sis.suspense_score    = _score_suspense(scene_draft)
    sis.info_gap_score    = _score_info_gap(scene_draft, position_pct)
    sis.emotional_contrast = _score_emotional_contrast(target_emotions or {}, previous_scores)
    sis.hook_strength     = _score_hook_strength(scene_draft, position_pct)
    sis.surprise_potential = _score_surprise_potential(scene_draft, beats_covered, position_pct)

    # Preliminary total for anti-monotony
    preliminary = _compute_sis_total(sis)
    sis.monotony_penalty = _monotony_penalty(preliminary, previous_scores)

    # Final SIS
    sis.sis_total = _compute_sis_total(sis)

    # Word count
    sis.word_count_min, sis.word_count_max, sis.word_count_target, sis.narrative_mode = \
        _allocate_words(sis.sis_total)

    # Scene type
    sis.scene_type = _infer_scene_type(beats_covered, position_pct)

    return sis


def allocate_word_counts(
    scene_scores: list[SceneInterestScore],
    total_chapter_words: int = 0,
) -> list[SceneInterestScore]:
    """
    Given a list of scored scenes, optionally rescale word counts to hit
    a total chapter word count target.

    Args:
        scene_scores: list of SceneInterestScore objects
        total_chapter_words: if > 0, rescale proportionally to hit this total

    Returns:
        Updated list (in-place modification, also returned)
    """
    if not scene_scores:
        return scene_scores

    if total_chapter_words > 0:
        raw_total = sum(s.word_count_target for s in scene_scores)
        if raw_total > 0:
            scale = total_chapter_words / raw_total
            for s in scene_scores:
                s.word_count_target = max(200, int(s.word_count_target * scale))
                s.word_count_min    = max(100, int(s.word_count_min * scale))
                s.word_count_max    = max(300, int(s.word_count_max * scale))

    return scene_scores


def validate_interest_curve(scene_scores: list[SceneInterestScore]) -> list[str]:
    """
    Validate the interest curve for anti-monotony and pacing rules.
    Returns a list of warnings (empty = curve is OK).

    Rules:
    - No 2+ consecutive scenes both ≥ 80 SIS
    - No 2+ consecutive scenes both ≤ 35 SIS
    - Total interest (avg SIS) should be ≥ 45
    - Last scene before finale should be HIGH (≥ 70)
    """
    warnings = []

    if not scene_scores:
        return warnings

    # Anti-monotony
    for i in range(1, len(scene_scores)):
        prev = scene_scores[i - 1].sis_total
        curr = scene_scores[i].sis_total
        if prev >= HIGH_THRESHOLD and curr >= HIGH_THRESHOLD:
            warnings.append(
                f"Scenes {i} and {i+1} both high SIS ({prev:.0f}, {curr:.0f}) — "
                f"insert a reflection/sequel scene between them"
            )
        if prev <= LOW_THRESHOLD and curr <= LOW_THRESHOLD:
            warnings.append(
                f"Scenes {i} and {i+1} both low SIS ({prev:.0f}, {curr:.0f}) — "
                f"compress one or inject a hook"
            )

    # Average interest
    avg = sum(s.sis_total for s in scene_scores) / len(scene_scores)
    if avg < 45:
        warnings.append(f"Average SIS={avg:.1f} is too low (<45) — chapter may feel flat")

    # Pre-finale peak
    if len(scene_scores) >= 3:
        pre_finale = scene_scores[-2].sis_total
        if pre_finale < 60:
            warnings.append(
                f"Scene before finale has SIS={pre_finale:.0f} (<60) — "
                f"build momentum going into the climax"
            )

    return warnings


def scene_interest_report(scene_scores: list[SceneInterestScore]) -> str:
    """Human-readable interest curve report."""
    lines = [
        "─── Scene Interest Score Report ────────────────────────────",
        f"{'#':<4} {'SIS':>5} {'Mode':<10} {'Words':>6} {'Beat':<22} {'Type':<12}",
        "─" * 68,
    ]
    for i, s in enumerate(scene_scores):
        lines.append(
            f"{i+1:<4} {s.sis_total:>5.1f} {s.narrative_mode:<10} "
            f"{s.word_count_target:>6,} {s.beat_name:<22} {s.scene_type:<12}"
        )

    avg = sum(s.sis_total for s in scene_scores) / len(scene_scores) if scene_scores else 0
    total_words = sum(s.word_count_target for s in scene_scores)
    lines += [
        "─" * 68,
        f"Average SIS: {avg:.1f}  |  Total words: {total_words:,}",
    ]

    warnings = validate_interest_curve(scene_scores)
    if warnings:
        lines.append("\nWarnings:")
        for w in warnings:
            lines.append(f"  ⚠  {w}")

    return "\n".join(lines)


def _split_chapter_into_scenes(chapter_text: str) -> list[str]:
    """Split chapter prose into scene-sized chunks for SIS scoring."""
    body = re.sub(r"^#.*$", "", chapter_text, flags=re.MULTILINE).strip()
    scenes = [s.strip() for s in re.split(r"\n---+\n", body) if s.strip()]
    if len(scenes) > 1:
        return scenes

    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if len(paragraphs) <= 3:
        return [body] if body else []

    chunk_count = min(5, max(2, len(paragraphs) // 4))
    chunk_size = max(1, len(paragraphs) // chunk_count)
    return [
        "\n\n".join(paragraphs[i : i + chunk_size])
        for i in range(0, len(paragraphs), chunk_size)
        if paragraphs[i : i + chunk_size]
    ]


def score_chapter_scenes_from_prose(
    chapter_text: str,
    chapter_plan=None,
    genre_model=None,
) -> tuple[list[SceneInterestScore], list[str]]:
    """
    Score written chapter prose scene-by-scene and validate the interest curve.

    Returns:
        (scene_scores, curve_warnings)
    """
    scenes = _split_chapter_into_scenes(chapter_text)
    if not scenes:
        return [], []

    position_pct = getattr(chapter_plan, "position_pct", 0.5) if chapter_plan else 0.5
    target_emotions = getattr(chapter_plan, "target_emotions", {}) or {}
    if genre_model and chapter_plan and not target_emotions:
        target_emotions = genre_model.suggest_chapter_emotions(
            position_pct, getattr(chapter_plan, "arc_type", "Man in Hole")
        )

    planned_beats: list[list] = []
    if chapter_plan and getattr(chapter_plan, "scenes", None):
        planned_beats = [sd.get("beats_covered", []) for sd in chapter_plan.scenes]

    default_beats = getattr(chapter_plan, "beats_covered", []) if chapter_plan else []

    scene_scores: list[SceneInterestScore] = []
    previous: list[SceneInterestScore] = []
    for i, scene_text in enumerate(scenes):
        beats = planned_beats[i] if i < len(planned_beats) else default_beats
        sis = score_scene(
            scene_draft=scene_text[:2500],
            beats_covered=beats,
            position_pct=position_pct,
            previous_scores=previous,
            target_emotions=target_emotions,
        )
        scene_scores.append(sis)
        previous.append(sis)

    return scene_scores, validate_interest_curve(scene_scores)
