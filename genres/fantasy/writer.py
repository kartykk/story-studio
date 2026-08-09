"""
genres/fantasy/writer.py — Fantasy genre model.
"""

from genres.base_genre import BaseGenreModel
from genres.fantasy import config, psychology, characters


class FantasyGenreModel(BaseGenreModel):

    @property
    def genre(self) -> str:
        return "fantasy"

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

    def system_prompt_addon(self, bible) -> str:
        subgenre = getattr(bible, "subgenre", "")
        subgenre_cfg = config.SUBGENRE_CONFIGS.get(subgenre, {})
        return f"""
## Fantasy Genre Model — Writing Rules

**Genre:** Fantasy ({subgenre or "General"})
**Arc:** {", ".join(config.RECOMMENDED_ARC_TYPES)}
**Chapter length:** {config.CHAPTER_LENGTH_WORDS[0]:,}-{config.CHAPTER_LENGTH_WORDS[1]:,} words

### Worldbuilding Rule (CRITICAL)
**DO NOT front-load information.** Information before emotional investment = reader abandonment.
Reveal the world THROUGH: dialogue, conflict, character observation, small moments.
Include ONLY what's critical to the character's present moment.
Magic: introduce one new element per chapter maximum.

### Reader Psychology (Bettelheim + Campbell)
Fantasy readers need: {", ".join(psychology.READER_CORE_NEEDS)}

### The Chosen One (if applicable)
Works because: {psychology.CHOSEN_ONE_PSYCHOLOGY["why_works"]}
Appeal: {psychology.CHOSEN_ONE_PSYCHOLOGY["core_appeal"]}

### Mentor Rules
- Mentor MUST have flaws — omniscient mentor kills reader investment
- Mentor MUST depart (death, sacrifice, limitation revealed) by {int(config.MENTOR_DEPARTURE_PCT[1]*100)}%
- Departure function: grief + forced self-reliance = protagonist's transformation

### Sense of Wonder Triggers
{chr(10).join(f"- {t}" for t in psychology.SENSE_OF_WONDER_TRIGGERS)}

### What Satisfies Fantasy Readers
{chr(10).join(f"- {k}: {v}" for k, v in psychology.SATISFACTION_TRIGGERS.items())}

### What Fails Fantasy Readers
{chr(10).join(f"- {k}" for k in psychology.DISSATISFACTION_TRIGGERS)}

### Tone: {subgenre_cfg.get("tone", "Epic, wondrous, high stakes")}
### Magic cost: Every magical ability must have a cost or limitation — power without cost feels cheap
"""

    def chapter_writing_instructions(self, bible, chapter_plan, scene_scores: list) -> str:
        position = getattr(chapter_plan, "position_pct", 0.5)
        target_emotions = getattr(chapter_plan, "target_emotions", config.TARGET_EMOTIONS)

        if position < 0.10:
            beat_guidance = "ORDINARY WORLD: Establish the protagonist's world — hint at more. Introduce ONE wonder."
        elif position < 0.20:
            beat_guidance = "CALL TO ADVENTURE: The call arrives. Chosen One revelation or inciting magic. First wonder paid off."
        elif position < 0.40:
            beat_guidance = "ENTERING THE NEW WORLD: Tests, allies, enemies. Mentor relationship deepens. World expands."
        elif position < 0.55:
            beat_guidance = "MIDPOINT: Ordeal. Real cost paid. Character has changed — can't go back."
        elif position < 0.65:
            beat_guidance = "MENTOR DEPARTURE ZONE: Mentor departs or is lost. Protagonist must stand alone."
        elif position < 0.82:
            beat_guidance = "DARK NIGHT: Supreme ordeal. All seems lost. The lie must be defeated."
        else:
            beat_guidance = "CLIMAX/RETURN: Hero earns destiny. Eucatastrophe. The world is changed."

        return f"""
### Chapter {chapter_plan.number} — Fantasy Writing Instructions

**Position:** {position:.0%} through story
**Beat:** {beat_guidance}
**Target emotions:** {", ".join(f"{k} {v:.0%}" for k, v in target_emotions.items() if v > 0.3)}
**Word count:** {getattr(chapter_plan, 'word_count_target', 5000):,} words

### This Chapter Must:
- Reveal ONE new element of the world or magic system — not more
- Show consequence of magic (cost, limitation, or unexpected result)
- Move the hero's arc forward (not just the plot)
- End with either: wonder, dread, or decision point
- Dialogue should reveal world without info-dumping — characters explain to each other only what makes sense to explain

### Pacing (fantasy-specific):
- Fantasy chapters are longer — use the space for depth, not filler
- Action sequences: short sentences, no description. Aftermath: expansive, emotional.
- Every chapter should have one moment of genuine wonder or dread
"""

    def character_building_prompt(self, role: str, tier: int, subgenre: str = "") -> str:
        if role in ("protagonist", "chosen_one", "hero"):
            arch = characters.CHOSEN_ONE_ARCHETYPE
        elif role in ("antagonist", "dark_lord", "villain"):
            arch = characters.DARK_LORD_ARCHETYPE
        elif role == "mentor":
            arch = characters.MENTOR_ARCHETYPE
        else:
            arch = characters.ALLY_ARCHETYPE

        if tier == 3:
            return f"Create a minor fantasy character: {role}. One memorable trait. Clear function in the world."

        ghost_opts = "\n".join(f"  - {g}" for g in arch.get("ghost_templates", []))

        return f"""Create a Tier {tier} fantasy character with role: {role}

**Vogler archetype:** {arch.get("vogler_archetype", "")}
**Jungian:** {arch.get("jungian", "")}
**Enneagram:** {arch.get("enneagram", "")}
**Speech pattern:** {arch.get("speech_pattern", "")}
**Arc:** {arch.get("arc", "")}

**Ghost/Wound:**
{ghost_opts}

**Lie:** {arch.get("lie", "")}
**Want:** {arch.get("want", "")}
**Need:** {arch.get("need", "")}

**Flaws required:** {arch.get("flaws_required", arch.get("flaw_required", "Yes — no perfect characters"))}
**Rule:** {arch.get("psychology", arch.get("motivation", "Believable, specific, not generic"))}

Build with: specific cultural origin, specific magical limitation or ability, specific relationship to the world's history."""

    def validate_story_rules(self, bible) -> list[str]:
        violations = []
        if not bible.world.magic_or_tech:
            violations.append("No magic system defined in WorldBible. Fantasy requires at least basic magic rules.")

        mentor_chars = [c for c in bible.characters.values()
                        if c.role in ("mentor", "Mentor")]
        if not mentor_chars and len(bible.characters) > 2:
            violations.append("No Mentor character found. Fantasy benefits strongly from a mentor figure.")

        return violations

    def suggest_chapter_emotions(self, position_pct: float, arc_type: str) -> dict:
        if position_pct < 0.12:
            return {"anticipation": 0.55, "joy": 0.50, "trust": 0.45}
        elif position_pct < 0.25:
            return {"anticipation": 0.75, "surprise": 0.65, "joy": 0.55, "fear": 0.30}
        elif position_pct < 0.50:
            return {"anticipation": 0.70, "joy": 0.60, "trust": 0.60, "fear": 0.40}
        elif position_pct < 0.65:
            return {"fear": 0.65, "anticipation": 0.65, "sadness": 0.50, "trust": 0.40}
        elif position_pct < 0.82:
            return {"sadness": 0.65, "fear": 0.70, "anticipation": 0.60, "anger": 0.40}
        else:
            return {"joy": 0.80, "trust": 0.70, "surprise": 0.65, "anticipation": 0.50}

    def get_reader_psychology(self) -> dict:
        return {
            "core_needs":              psychology.READER_CORE_NEEDS,
            "satisfaction_triggers":   psychology.SATISFACTION_TRIGGERS,
            "dissatisfaction_triggers": psychology.DISSATISFACTION_TRIGGERS,
            "suspense_weights":        psychology.SUSPENSE_WEIGHTS,
        }

    def suggested_character_count(self) -> dict:
        return characters.SUGGESTED_CHARACTER_COUNT

    def detect_subgenre(self, premise: str, tone: str = "") -> str:
        p = premise.lower()
        t = tone.lower()
        if any(k in p for k in ["cozy", "tea", "bakery", "gentle", "village", "warm"]):
            return "Cozy Fantasy"
        if any(k in p for k in ["grim", "dark", "brutal", "grimdark", "morally", "no heroes"]):
            return "Grimdark"
        if any(k in p for k in ["city", "modern", "urban", "contemporary", "street", "apartment"]):
            return "Urban Fantasy"
        if any(k in p for k in ["dark", "sinister", "corrupt", "fallen"]) and "dark" in t:
            return "Dark Fantasy"
        return "High Fantasy"
