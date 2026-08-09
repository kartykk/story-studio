"""
quality_gate.py — Chapter quality scoring and auto-retry gate.

Research foundation:
- 5-axis scoring model used by professional editors and writing instructors
- Axis 1: Emotional Resonance — measured via DeepSeek emotion consistency
- Axis 2: Narrative Craft — prose quality indicators (Aristotle's Poetics + Vogler)
- Axis 3: Pacing — Scene Interest Score average + variance
- Axis 4: Character Authenticity — dialogue/action consistent with character profile
- Axis 5: Genre Adherence — genre-specific rules followed (from genre model)

Weighted formula:
  Total = (ER×0.30) + (NC×0.25) + (PA×0.20) + (CA×0.15) + (GA×0.10)

Quality thresholds per genre:
  Crime: 68 | Romance: 72 | Horror: 65 | Fantasy: 70 | Literary: 75

Claude model allocation:
  Writing:  claude-opus-4-6   (highest quality generation)
  Scoring:  claude-sonnet-4-6 (fast, accurate scoring at lower cost)
"""

import os
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from core.emotion_scorer import EmotionScore, emotion_consistency, score_chapter, score_text
from core.interest_scorer import score_chapter_scenes_from_prose
from core.arc_calculator import get_target_intensity


# ── Constants ─────────────────────────────────────────────────────────────────

SCORING_MODEL = "claude-sonnet-4-6"    # cost-efficient for scoring
WRITING_MODEL = "claude-opus-4-6"      # best for generation

ANTHROPIC_BASE_URL = "https://api.anthropic.com"

MAX_RETRY_ATTEMPTS = 3

# Axis weights
AXIS_WEIGHTS = {
    "emotional_resonance":  0.30,
    "narrative_craft":      0.25,
    "pacing":               0.20,
    "character_auth":       0.15,
    "genre_adherence":      0.10,
}

# Genre quality thresholds (score must exceed to pass)
GENRE_THRESHOLDS = {
    "crime":    68,
    "romance":  72,
    "horror":   65,
    "fantasy":  70,
    "literary": 75,
    "default":  68,
}

# Expected cliffhanger rate when genre config omits CLIFFHANGER_RATE
GENRE_CLIFFHANGER_RATES = {
    "crime":    0.80,
    "horror":   0.75,
    "romance":  0.60,
    "fantasy":  0.70,
    "literary": 0.40,
}

HOOK_ENDING_KEYWORDS = [
    "suddenly", "but", "except", "however", "wait", "wrong", "mistake",
    "realised", "realized", "phone rang", "door opened", "shot rang",
    "everything changed", "didn't know", "never expected", "until",
    "?", "revelation", "discovered", "found", "dead", "gone", "missing",
]


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class AxisScore:
    name: str           = ""
    score: float        = 0.0    # 0-100
    weight: float       = 0.0
    rationale: str      = ""
    top_issue: str      = ""     # single most important problem found


@dataclass
class QualityReport:
    # Per-axis scores
    emotional_resonance:  AxisScore = field(default_factory=lambda: AxisScore("emotional_resonance", weight=0.30))
    narrative_craft:      AxisScore = field(default_factory=lambda: AxisScore("narrative_craft",     weight=0.25))
    pacing:               AxisScore = field(default_factory=lambda: AxisScore("pacing",             weight=0.20))
    character_auth:       AxisScore = field(default_factory=lambda: AxisScore("character_auth",     weight=0.15))
    genre_adherence:      AxisScore = field(default_factory=lambda: AxisScore("genre_adherence",    weight=0.10))

    # Final
    total_score:          float = 0.0     # 0-100
    threshold:            float = 68.0
    passed:               bool  = False

    # Metadata
    chapter_number:       int   = 0
    attempt:              int   = 1
    word_count:           int   = 0

    # Regeneration guidance
    top_issues:           list  = field(default_factory=list)    # top 3 problems
    regeneration_focus:   str   = ""    # what to fix in the next attempt

    def to_dict(self) -> dict:
        return {
            "emotional_resonance":  asdict(self.emotional_resonance),
            "narrative_craft":      asdict(self.narrative_craft),
            "pacing":               asdict(self.pacing),
            "character_auth":       asdict(self.character_auth),
            "genre_adherence":      asdict(self.genre_adherence),
            "total_score":          self.total_score,
            "threshold":            self.threshold,
            "passed":               self.passed,
            "chapter_number":       self.chapter_number,
            "attempt":              self.attempt,
            "word_count":           self.word_count,
            "top_issues":           self.top_issues,
            "regeneration_focus":   self.regeneration_focus,
        }

    def summary(self) -> str:
        status = "PASS ✓" if self.passed else "FAIL ✗"
        lines = [
            f"── Quality Gate: Chapter {self.chapter_number} (Attempt {self.attempt}) ──",
            f"  Total Score: {self.total_score:.1f} / 100  [{status}]  (threshold: {self.threshold:.0f})",
            f"  Emotional Resonance:  {self.emotional_resonance.score:.1f}",
            f"  Narrative Craft:      {self.narrative_craft.score:.1f}",
            f"  Pacing:               {self.pacing.score:.1f}",
            f"  Character Auth:       {self.character_auth.score:.1f}",
            f"  Genre Adherence:      {self.genre_adherence.score:.1f}",
        ]
        if self.top_issues:
            lines.append("  Issues:")
            for issue in self.top_issues:
                lines.append(f"    • {issue}")
        return "\n".join(lines)


# ── Anthropic Client ──────────────────────────────────────────────────────────

def _anthropic_client():
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key or api_key.startswith("your_"):
            return None
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


# ── Scoring Prompts ───────────────────────────────────────────────────────────

_QUALITY_SCORING_PROMPT = """You are a professional story editor scoring a chapter on 5 axes.
Be rigorous and honest. Bad chapters should score 40-60. Great chapters should score 80-95.

Chapter to score:
\"\"\"
{chapter_text}
\"\"\"

Genre: {genre}
Chapter Number: {chapter_number} of {total_chapters}
Chapter emotional goal: {emotional_goal}
Character profiles (brief):
{character_summaries}

Score each axis 0-100 and give a brief rationale + the top issue for each:

1. EMOTIONAL_RESONANCE (0-100): Does this chapter achieve its emotional goal?
   - Does the reader FEEL the target emotion?
   - Are emotions earned through specific concrete detail (not just stated)?
   - Is there emotional arc within the chapter (start vs end feeling)?

2. NARRATIVE_CRAFT (0-100): Quality of writing execution.
   - Show vs tell ratio (showing = higher score)
   - Specific concrete details vs vague abstraction
   - Dialogue naturalism — do characters sound like real distinct people?
   - Sentence variety and rhythm
   - Opening hook and closing beat

3. PACING (0-100): Scene flow and reader engagement.
   - Does pacing match the chapter's position in story? (climax chapter must be fast)
   - Are high-importance moments given enough space?
   - Are transitions smooth?
   - Does the chapter end with appropriate momentum for the next?

4. CHARACTER_AUTHENTICITY (0-100): Do characters behave consistently?
   - Does each character's dialogue reflect their stated speech pattern?
   - Do character decisions follow from their established psychology (Ghost/Lie/Want/Need)?
   - Are character reactions proportionate and believable?
   - Is the POV character's inner voice consistent?

5. GENRE_ADHERENCE (0-100): Does this chapter follow genre conventions?
   Genre: {genre}
   - Are genre-specific conventions present?
   - Does the chapter serve the genre reader's core expectations?
   - Any genre rule violations?

Return ONLY valid JSON:
{{
  "emotional_resonance": {{
    "score": 0,
    "rationale": "...",
    "top_issue": "..."
  }},
  "narrative_craft": {{
    "score": 0,
    "rationale": "...",
    "top_issue": "..."
  }},
  "pacing": {{
    "score": 0,
    "rationale": "...",
    "top_issue": "..."
  }},
  "character_auth": {{
    "score": 0,
    "rationale": "...",
    "top_issue": "..."
  }},
  "genre_adherence": {{
    "score": 0,
    "rationale": "...",
    "top_issue": "..."
  }}
}}"""


def _parse_quality_json(raw: str) -> Optional[dict]:
    """Parse Claude's JSON response, handle markdown fences."""
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


# ── Axis Scorers ──────────────────────────────────────────────────────────────

def _score_emotional_resonance_local(
    chapter_text: str,
    emotion_score: Optional[EmotionScore],
    target_emotions: dict,
    emotional_goal: str,
) -> AxisScore:
    """
    If we have a DeepSeek emotion score, use cosine similarity vs target.
    Otherwise, use keyword heuristics.
    """
    ax = AxisScore("emotional_resonance", weight=AXIS_WEIGHTS["emotional_resonance"])

    if emotion_score and target_emotions:
        consistency = emotion_consistency(emotion_score, target_emotions)
        ax.score = round(consistency * 100, 1)
        ax.rationale = (
            f"Emotion consistency score: {consistency:.2f}. "
            f"Dominant emotion detected: {emotion_score.dominant_emotion} "
            f"(intensity: {emotion_score.intensity:.2f})"
        )
        if consistency < 0.5:
            ax.top_issue = f"Emotional mismatch — target: {max(target_emotions, key=target_emotions.get)}, detected: {emotion_score.dominant_emotion}"
        elif consistency < 0.7:
            ax.top_issue = f"Weak emotional alignment — strengthen {max(target_emotions, key=target_emotions.get)} moments"
        else:
            ax.top_issue = ""
    else:
        # Heuristic fallback
        ax.score = 60.0
        ax.rationale = "Estimated (no DeepSeek score available)"
        ax.top_issue = "Run with DEEPSEEK_API_KEY for precise emotion scoring"

    return ax


def _score_pacing_local(
    scene_scores: list,
    chapter_position_pct: float,
) -> AxisScore:
    """Score pacing from Scene Interest Score data."""
    ax = AxisScore("pacing", weight=AXIS_WEIGHTS["pacing"])

    if not scene_scores:
        ax.score = 55.0
        ax.rationale = "No scene scores available"
        ax.top_issue = "Score individual scenes for precise pacing analysis"
        return ax

    avg_sis = sum(s.sis_total for s in scene_scores) / len(scene_scores)

    # At climax (0.80+), expect high average SIS
    if chapter_position_pct > 0.80:
        target_avg = 70.0
    elif chapter_position_pct > 0.50:
        target_avg = 60.0
    else:
        target_avg = 50.0

    gap = abs(avg_sis - target_avg)
    ax.score = max(0.0, 100.0 - gap * 2.0)

    # Variance check — monotony penalty
    if len(scene_scores) >= 3:
        variance = sum((s.sis_total - avg_sis) ** 2 for s in scene_scores) / len(scene_scores)
        if variance < 100:   # std dev < 10 — too flat
            ax.score = max(0.0, ax.score - 15.0)
            ax.top_issue = f"Pacing too flat (avg SIS={avg_sis:.0f}, variance={variance:.0f}) — add variety"
        else:
            ax.top_issue = ""

    ax.rationale = f"Average SIS: {avg_sis:.1f} (target: {target_avg:.0f} at {chapter_position_pct:.0%} position)"
    ax.score = round(ax.score, 1)
    return ax


def _cliffhanger_rate_for_genre(genre: str) -> float:
    try:
        mod = __import__(f"genres.{genre.lower()}.config", fromlist=["CLIFFHANGER_RATE"])
        return float(getattr(mod, "CLIFFHANGER_RATE", GENRE_CLIFFHANGER_RATES.get(genre.lower(), 0.65)))
    except (ImportError, AttributeError, ValueError):
        return GENRE_CLIFFHANGER_RATES.get(genre.lower(), 0.65)


def _check_chapter_ending_hook(chapter_text: str) -> tuple[bool, str]:
    """Heuristic: does the chapter end with a hook / cliffhanger?"""
    lines = [ln.strip() for ln in chapter_text.strip().split("\n") if ln.strip() and not ln.startswith("#")]
    if not lines:
        return False, "Chapter has no ending content"

    tail = " ".join(lines[-3:]).lower()
    if tail.strip().endswith("?"):
        return True, ""

    hits = sum(1 for kw in HOOK_ENDING_KEYWORDS if kw in tail)
    if hits >= 2:
        return True, ""
    if hits == 1 and len(lines[-1]) < 120:
        return True, ""

    return False, "Chapter ending lacks a hook — end with revelation, danger, or an unresolved question"


def _genre_rule_violations(
    bible,
    genre_model,
    chapter_number: int,
    chapter_text: str,
) -> list[str]:
    if not genre_model or not bible:
        return []

    backup = list(bible.chapters)
    existing = bible.get_chapter(chapter_number)
    try:
        if existing:
            existing["content"] = chapter_text
        else:
            bible.chapters.append({
                "number": chapter_number,
                "title": f"Chapter {chapter_number}",
                "content": chapter_text,
            })
        return genre_model.validate_story_rules(bible)
    finally:
        bible.chapters = backup


def _score_emotion_arc_drift(
    chapter_text: str,
    target_emotions: dict,
    emotional_arc_type: str,
    position_pct: float,
) -> tuple[float, str]:
    """
    Compare chapter emotional intensity/shape to Reagan arc target at this position.
    Returns (adjustment -20..+10, issue message).
    """
    try:
        chapter_data = score_chapter(chapter_text[:6000], sections=5)
    except Exception:
        return 0.0, ""

    overall = chapter_data.get("overall")
    if not overall:
        return 0.0, ""

    target_intensity = get_target_intensity(position_pct, emotional_arc_type or "Man in Hole")
    intensity_gap = abs(overall.intensity - target_intensity)

    adjustment = 0.0
    issues: list[str] = []

    # Opening chapters have more latitude — family-drama setup often reads as sadness
    drift_scale = 0.5 if position_pct < 0.25 else 1.0

    if intensity_gap > 0.25:
        adjustment -= min(20.0, intensity_gap * 40) * drift_scale
        issues.append(
            f"Emotional intensity {overall.intensity:.0%} vs arc target {target_intensity:.0%}"
        )

    if target_emotions:
        consistency = emotion_consistency(overall, target_emotions)
        if consistency < 0.45:
            adjustment -= min(15.0, (0.45 - consistency) * 50)
            dominant = max(target_emotions, key=target_emotions.get)
            issues.append(
                f"Chapter emotion drift — expected {dominant}, got {overall.dominant_emotion}"
            )

    arc_shape = chapter_data.get("arc_shape", "unknown")
    if position_pct > 0.75 and arc_shape == "falling":
        adjustment -= 10.0
        issues.append("Emotional arc falls before climax — build tension toward the finale")
    elif position_pct < 0.35 and arc_shape == "peak":
        adjustment -= 8.0
        issues.append("Emotional peak too early — reserve intensity for later chapters")

    return adjustment, "; ".join(issues)


def _collect_extra_issues(
    chapter_text: str,
    genre: str,
    bible,
    genre_model,
    chapter_number: int,
    chapter_plan,
    curve_warnings: list[str],
) -> list[str]:
    """Genre rules, cliffhanger, and interest-curve warnings."""
    extra: list[str] = list(curve_warnings or [])

    if genre_model and bible:
        extra.extend(_genre_rule_violations(bible, genre_model, chapter_number, chapter_text))

    rate = _cliffhanger_rate_for_genre(genre)
    if rate >= 0.55:
        has_hook, hook_issue = _check_chapter_ending_hook(chapter_text)
        if not has_hook and hook_issue:
            extra.append(hook_issue)

    return extra


# ── Public API ────────────────────────────────────────────────────────────────

def score_chapter_quality(
    chapter_text: str,
    chapter_number: int,
    total_chapters: int,
    genre: str,
    emotional_goal: str = "",
    target_emotions: dict = None,
    emotion_score: Optional[EmotionScore] = None,
    scene_scores: list = None,
    character_summaries: str = "",
    attempt: int = 1,
    genre_model=None,
    bible=None,
    chapter_plan=None,
    emotional_arc_type: str = "Man in Hole",
    extra_issues: list = None,
) -> QualityReport:
    """
    Score a chapter on 5 axes using Claude Sonnet for editorial analysis.
    Falls back to local heuristics if ANTHROPIC_API_KEY not set.

    Args:
        chapter_text: full written chapter content
        chapter_number: 1-indexed
        total_chapters: total chapters in story
        genre: crime / romance / horror / fantasy / literary
        emotional_goal: what the reader should feel (from ChapterPlan)
        target_emotions: dict like {"fear": 0.7, "anticipation": 0.8}
        emotion_score: pre-computed DeepSeek EmotionScore (optional)
        scene_scores: list of SceneInterestScore objects for this chapter
        character_summaries: compact character profiles for context
        attempt: which retry attempt this is

    Returns:
        QualityReport
    """
    threshold = GENRE_THRESHOLDS.get(genre.lower(), GENRE_THRESHOLDS["default"])
    position_pct = (chapter_number - 0.5) / max(total_chapters, 1)

    report = QualityReport(
        chapter_number=chapter_number,
        attempt=attempt,
        word_count=len(chapter_text.split()),
        threshold=threshold,
    )

    # ── Try Claude Sonnet for axes 1,2,4,5 ──
    client = _anthropic_client()
    if client:
        prompt = _QUALITY_SCORING_PROMPT.format(
            chapter_text=chapter_text[:8000],    # cap to avoid huge prompts
            genre=genre,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            emotional_goal=emotional_goal,
            character_summaries=character_summaries[:2000],
        )

        try:
            resp = client.messages.create(
                model=SCORING_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            data = _parse_quality_json(raw)

            if data:
                for axis_name in ["emotional_resonance", "narrative_craft", "character_auth", "genre_adherence"]:
                    ax_data = data.get(axis_name, {})
                    ax = AxisScore(
                        name=axis_name,
                        score=float(ax_data.get("score", 60.0)),
                        weight=AXIS_WEIGHTS.get(axis_name, 0.1),
                        rationale=ax_data.get("rationale", ""),
                        top_issue=ax_data.get("top_issue", ""),
                    )
                    setattr(report, axis_name, ax)

        except Exception as e:
            print(f"  [quality_gate] Claude scoring error: {e}")
            # Fall through to heuristic scoring

    # ── Local scoring for axes with data ──

    # Emotional resonance — supplement/override with DeepSeek if available
    if emotion_score or target_emotions:
        report.emotional_resonance = _score_emotional_resonance_local(
            chapter_text, emotion_score, target_emotions or {}, emotional_goal
        )

    # Pacing — from scene scores (prose-based when available)
    report.pacing = _score_pacing_local(scene_scores or [], position_pct)

    # Emotion arc drift adjustment
    arc_drift_adj, arc_issue = _score_emotion_arc_drift(
        chapter_text,
        target_emotions or {},
        emotional_arc_type,
        position_pct,
    )
    if arc_drift_adj:
        report.emotional_resonance.score = round(
            max(0.0, report.emotional_resonance.score + arc_drift_adj), 1
        )
        if arc_issue:
            report.emotional_resonance.top_issue = arc_issue

    # Penalize genre adherence for structural violations
    structural = extra_issues or []
    if structural:
        penalty = min(25.0, len(structural) * 8.0)
        report.genre_adherence.score = round(max(0.0, report.genre_adherence.score - penalty), 1)
        if not report.genre_adherence.top_issue:
            report.genre_adherence.top_issue = structural[0]

    # ── Compute weighted total ──
    report.total_score = round(
        report.emotional_resonance.score * AXIS_WEIGHTS["emotional_resonance"] +
        report.narrative_craft.score     * AXIS_WEIGHTS["narrative_craft"] +
        report.pacing.score              * AXIS_WEIGHTS["pacing"] +
        report.character_auth.score      * AXIS_WEIGHTS["character_auth"] +
        report.genre_adherence.score     * AXIS_WEIGHTS["genre_adherence"],
        1
    )

    report.passed = report.total_score >= threshold

    # ── Collect top issues for regeneration ──
    all_issues = []
    for axis in [report.emotional_resonance, report.narrative_craft, report.pacing,
                 report.character_auth, report.genre_adherence]:
        if axis.top_issue:
            all_issues.append((axis.score, axis.top_issue))

    for issue in structural:
        all_issues.append((40.0, issue))

    all_issues.sort(key=lambda x: x[0])   # worst scores first
    report.top_issues = [issue for _, issue in all_issues[:5]]

    # ── Regeneration focus ──
    if not report.passed and report.top_issues:
        report.regeneration_focus = build_regeneration_prompt(report)

    return report


def build_regeneration_prompt(report: QualityReport) -> str:
    """
    Build a concise regeneration instruction for Claude when a chapter fails.
    Focuses on the lowest-scoring axes only.

    Returns:
        str: instructions to append to the next write_chapter() call
    """
    axes = [
        report.emotional_resonance,
        report.narrative_craft,
        report.pacing,
        report.character_auth,
        report.genre_adherence,
    ]
    axes.sort(key=lambda a: a.score)    # worst first
    weak = [a for a in axes if a.score < 70][:3]

    if not weak:
        return "Refine for higher overall quality — strengthen the weakest moments."

    instructions = [
        f"Previous attempt scored {report.total_score:.0f}/100 (threshold: {report.threshold:.0f}). "
        "Focus on these specific weaknesses:"
    ]
    for i, ax in enumerate(weak, 1):
        instructions.append(
            f"  {i}. {ax.name.replace('_',' ').title()} ({ax.score:.0f}/100): {ax.top_issue}"
        )

    instructions.append(
        "\nDo NOT change the plot. Rewrite the prose to fix only these issues."
    )

    return "\n".join(instructions)


def gate_chapter(
    chapter_text: str,
    chapter_number: int,
    total_chapters: int,
    genre: str,
    write_fn,
    **score_kwargs,
) -> tuple[str, QualityReport]:
    """
    Auto-retry loop: score → if fail → regenerate → repeat up to MAX_RETRY_ATTEMPTS.

    Args:
        chapter_text: initial chapter draft
        chapter_number: 1-indexed chapter number
        total_chapters: total chapters in story
        genre: genre name
        write_fn: callable(regeneration_focus: str) -> str  — generates new chapter text
        **score_kwargs: passed through to score_chapter_quality()

    Returns:
        (best_chapter_text, final_report)
    """
    best_text   = chapter_text
    best_report = None

    cp = score_kwargs.get("chapter_plan")
    genre_model = score_kwargs.get("genre_model")
    bible = score_kwargs.get("bible")
    emotional_arc_type = score_kwargs.get("emotional_arc_type", "Man in Hole")

    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        emotion_score = None
        try:
            emotion_score = score_text(chapter_text[:2000])
        except Exception:
            pass

        prose_scene_scores, curve_warnings = score_chapter_scenes_from_prose(
            chapter_text, cp, genre_model
        )
        extra_issues = _collect_extra_issues(
            chapter_text,
            genre,
            bible,
            genre_model,
            chapter_number,
            cp,
            curve_warnings,
        )

        report = score_chapter_quality(
            chapter_text=chapter_text,
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            genre=genre,
            attempt=attempt,
            emotion_score=emotion_score,
            scene_scores=prose_scene_scores or score_kwargs.get("scene_scores") or [],
            extra_issues=extra_issues,
            **{k: v for k, v in score_kwargs.items()
               if k not in ("scene_scores", "emotion_score", "genre_model", "bible", "chapter_plan")},
        )

        print(report.summary())

        if report.passed:
            return chapter_text, report

        if best_report is None or report.total_score > best_report.total_score:
            best_text   = chapter_text
            best_report = report

        if attempt < MAX_RETRY_ATTEMPTS:
            print(f"  [quality_gate] Attempt {attempt} failed ({report.total_score:.1f}). Regenerating...")
            try:
                chapter_text = write_fn(regeneration_focus=report.regeneration_focus)
            except Exception as e:
                print(f"  [quality_gate] Regeneration error: {e}")
                break

    print(f"  [quality_gate] Max attempts reached. Best score: {best_report.total_score:.1f}")
    return best_text, best_report
