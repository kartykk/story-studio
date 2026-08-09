"""
genres/crime/writer.py — Crime genre model (implements BaseGenreModel).
"""

from genres.base_genre import BaseGenreModel
from genres.crime import config, psychology, characters


class CrimeGenreModel(BaseGenreModel):

    @property
    def genre(self) -> str:
        return "crime"

    @property
    def subgenres(self) -> list[str]:
        return config.SUBGENRES

    @property
    def recommended_arc_types(self) -> list[str]:
        return config.RECOMMENDED_ARC_TYPES

    @property
    def quality_threshold(self) -> int:
        return config.QUALITY_THRESHOLD

    @property
    def chapter_length_range(self) -> tuple[int, int]:
        return config.CHAPTER_LENGTH_WORDS

    # ── Claude Prompt Extensions ──────────────────────────────────────────────

    def system_prompt_addon(self, bible) -> str:
        subgenre = getattr(bible, "subgenre", "")
        subgenre_cfg = config.SUBGENRE_CONFIGS.get(subgenre, {})
        arc_note = subgenre_cfg.get("arc_types", config.RECOMMENDED_ARC_TYPES)

        return f"""
## Crime Genre Model — Writing Rules

**Genre:** Crime Fiction ({subgenre or "General"})
**Arc:** {", ".join(arc_note)}
**Pacing:** {int(config.SCENE_SEQUEL_RATIO * 100)}% action / {int((1 - config.SCENE_SEQUEL_RATIO) * 100)}% reflection
**Chapter length:** {config.CHAPTER_LENGTH_WORDS[0]:,}-{config.CHAPTER_LENGTH_WORDS[1]:,} words

### Reader Psychology
Crime readers need: {", ".join(psychology.READER_CORE_NEEDS)}

### Mandatory Rules
1. **Crime occurs before {int(config.INCITING_INCIDENT_PCT * 100)}%** — the inciting crime must happen early
2. **Culprit introduced before 50%** — never introduce the real killer in the final chapters
3. **{int(config.RED_HERRING_COUNT[0])}-{int(config.RED_HERRING_COUNT[1])} red herrings** — each must spring from character psychology, not arbitrary plot
4. **Fair play rule** — every red herring must have a real clue the reader could find in hindsight
5. **No coincidence solutions** — the detective must solve through deduction, not luck
6. **{int(config.CLIFFHANGER_RATE * 100)}% of chapters end with a hook** — revelation, danger, or new question
7. **Culprit reveal at ~{int(config.REVEAL_PCT * 100)}%** — not too early, not too late

### Suspense Formula (Brewer & Lichtenstein, r=0.8234)
Suspense = (Imminence × Importance × Foregroundedness) / (1 + Confidence)
- Keep confidence LOW — reader should never be certain of the outcome
- Foreground the threat — make the danger present in the reader's mind
- Importance = life/death or justice/injustice stakes

### What Satisfies Crime Readers
{chr(10).join(f"- {k}: {v}" for k, v in psychology.SATISFACTION_TRIGGERS.items())}

### What Fails Crime Readers
{chr(10).join(f"- {k}" for k in psychology.DISSATISFACTION_TRIGGERS)}

### Dialogue Style
- Detective: terse, precise, asks leading questions, observational
- Criminal: varies by education; always has a justification for their actions
- Never let a character explain more than necessary — subtext is suspense
"""

    def chapter_writing_instructions(self, bible, chapter_plan, scene_scores: list) -> str:
        position = getattr(chapter_plan, "position_pct", 0.5)
        target_emotions = getattr(chapter_plan, "target_emotions", config.TARGET_EMOTIONS)

        # Determine what structural beat this chapter hits
        if position < 0.10:
            beat_guidance = "OPENING: Establish the world, the detective, and the crime. Hook immediately."
        elif position < 0.15:
            beat_guidance = "CATALYST: The crime has been committed. Stakes are now clear. Speed up."
        elif position < 0.50:
            beat_guidance = "INVESTIGATION: Build clues, introduce suspects, plant red herrings. Each scene reveals or rules out."
        elif position < 0.60:
            beat_guidance = "MIDPOINT: Stakes escalate. A new revelation changes everything. False victory or setback."
        elif position < 0.80:
            beat_guidance = "DARK VALLEY: Detective is wrong-footed. Red herring accepted as truth. All looks lost."
        elif position < 0.90:
            beat_guidance = "REVEAL: The truth emerges. Culprit unmasked. Justice moves toward resolution."
        else:
            beat_guidance = "RESOLUTION: Justice served (or denied in Noir). Emotional aftermath. Final image."

        return f"""
### Chapter {chapter_plan.number} — Crime Writing Instructions

**Position:** {position:.0%} through story
**Beat guidance:** {beat_guidance}
**Target emotions:** {", ".join(f"{k} {v:.0%}" for k, v in target_emotions.items() if v > 0.3)}
**Word count target:** {getattr(chapter_plan, 'word_count_target', 2000):,} words

### This Chapter Must:
- End with a hook (revelation, danger, or unresolved question)
- Move the investigation forward — reveal OR eliminate at least one suspect
- Show don't tell — no character should state what the reader can infer
- Keep the detective's internal reasoning visible but incomplete
- Plant one clue the reader could notice if they were paying attention

### Pacing:
- {int(config.SCENE_SEQUEL_RATIO * 100)}% of scenes should be active (investigation, confrontation, discovery)
- {int((1 - config.SCENE_SEQUEL_RATIO) * 100)}% reflection (detective thinking, personal moments that ground the story)
- Chapter length: {config.CHAPTER_LENGTH_WORDS[0]:,}-{config.CHAPTER_LENGTH_WORDS[1]:,} words

### Suspense Maintenance:
- Keep at least one unanswered question alive at all times
- Vary scene pace: fast interrogation → slower deduction → fast discovery
- Every piece of information should raise another question
"""

    def character_building_prompt(self, role: str, tier: int, subgenre: str = "") -> str:
        if role in ("protagonist", "detective"):
            arch = characters.DETECTIVE_ARCHETYPE
        elif role in ("antagonist", "criminal", "villain"):
            arch = characters.CRIMINAL_ARCHETYPE
        elif role == "victim":
            arch = characters.VICTIM_ARCHETYPE
        elif role == "corrupt_cop":
            arch = characters.CORRUPT_COP_ARCHETYPE
        else:
            arch = characters.WITNESS_ARCHETYPE

        if tier == 3:
            return (
                f"Create a minor crime fiction character with role: {role}. "
                f"Give them 3-5 specific traits (not generic). "
                f"One concrete detail that makes them memorable. "
                f"A clear function in the investigation (suspect/witness/obstacle)."
            )

        ghost_options = "\n".join(f"  - {g}" for g in arch.get("ghost_templates", []))
        lie_options   = "\n".join(f"  - {l}" for l in arch.get("lie_templates", []))
        flaw_options  = "\n".join(f"  - {f}" for f in arch.get("flaw_templates", []))

        return f"""Create a Tier {tier} crime fiction character with role: {role}

**Vogler Archetype:** {arch.get("vogler_archetype", "")}
**Enneagram options:** {", ".join(arch.get("enneagram_options", []))}
**MBTI options:** {", ".join(arch.get("mbti_options", []))}
**Speech pattern:** {arch.get("speech_pattern", "")}

**Ghost/Wound (choose or invent):**
{ghost_options}

**Lie they carry (choose or invent):**
{lie_options}

**Want (external goal):** {arch.get("want", "Relevant to the crime")}
**Need (internal truth):** {arch.get("need", "What they must learn")}

**Flaw options:**
{flaw_options}

**Psychology rule:** {arch.get("psychology_rule", "Make them believable and specific.")}
**Reader empathy:** {arch.get("reader_empathy_rule", "Reader should understand them.")}

Build this character with specific details — real name, specific backstory, distinctive voice.
Avoid generic archetypes. The ghost should directly cause their involvement in this crime."""

    def validate_story_rules(self, bible) -> list[str]:
        violations = []
        total = max(len(bible.chapters), 1)

        # Check culprit introduction
        char_names = [c.name.lower() for c in bible.characters.values()
                      if c.role in ("antagonist", "criminal", "villain")]
        if char_names:
            introduced_by = None
            for ch in bible.chapters:
                content = ch.get("content", "").lower()
                if any(name in content for name in char_names):
                    introduced_by = ch.get("number", 0)
                    break
            if introduced_by and introduced_by / total > 0.50:
                violations.append(
                    f"Culprit introduced too late (Chapter {introduced_by}/{total} = "
                    f"{introduced_by/total:.0%}). Must appear before 50%."
                )

        # Check tier 1 characters exist
        tier1 = [c for c in bible.characters.values() if c.tier == 1]
        if len(tier1) < 2:
            violations.append(
                f"Only {len(tier1)} Tier 1 character(s). Crime needs at least 2 "
                f"(detective + criminal)."
            )

        return violations

    def suggest_chapter_emotions(self, position_pct: float, arc_type: str) -> dict:
        """Crime emotion targets shift with story position."""
        if position_pct < 0.10:
            # Opening — curiosity, mild suspense
            return {"anticipation": 0.60, "surprise": 0.40, "fear": 0.30}
        elif position_pct < 0.30:
            # Investigation — building suspense
            return {"anticipation": 0.70, "fear": 0.50, "anger": 0.35}
        elif position_pct < 0.60:
            # Mid-story — escalation
            return {"anticipation": 0.75, "fear": 0.65, "anger": 0.45, "surprise": 0.55}
        elif position_pct < 0.80:
            # Dark valley — maximum tension
            return {"fear": 0.80, "anticipation": 0.75, "anger": 0.60, "sadness": 0.40}
        elif position_pct < 0.92:
            # Reveal — shock + relief
            return {"surprise": 0.85, "anticipation": 0.70, "anger": 0.55, "fear": 0.50}
        else:
            # Resolution
            return {"trust": 0.55, "sadness": 0.40, "anticipation": 0.25, "joy": 0.30}

    def get_reader_psychology(self) -> dict:
        return {
            "core_needs":              psychology.READER_CORE_NEEDS,
            "satisfaction_triggers":   psychology.SATISFACTION_TRIGGERS,
            "dissatisfaction_triggers": psychology.DISSATISFACTION_TRIGGERS,
            "suspense_weights":        psychology.SUSPENSE_FORMULA["weights"],
        }

    def suggested_character_count(self) -> dict:
        return characters.SUGGESTED_CHARACTER_COUNT

    def detect_subgenre(self, premise: str, tone: str = "") -> str:
        premise_lower = premise.lower()
        tone_lower    = tone.lower()
        if any(k in premise_lower for k in ["noir", "dark", "cynical", "fatalistic"]):
            return "Noir"
        if any(k in premise_lower for k in ["police", "cop", "detective", "precinct", "fbi", "cbi"]):
            return "Police Procedural"
        if any(k in premise_lower for k in ["psychological", "unreliable", "mind", "paranoia"]):
            return "Psychological Thriller"
        if any(k in premise_lower for k in ["heist", "robbery", "steal", "vault", "gang"]):
            return "Heist"
        if any(k in premise_lower for k in ["court", "lawyer", "trial", "legal", "judge"]):
            return "Legal Thriller"
        if any(k in premise_lower for k in ["cozy", "village", "amateur", "bakery", "knitting"]):
            return "Cozy Mystery"
        if "dark" in tone_lower or "grim" in tone_lower:
            return "Noir"
        return "Police Procedural"
