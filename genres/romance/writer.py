"""
genres/romance/writer.py — Romance genre model.
"""

from genres.base_genre import BaseGenreModel
from genres.romance import config, psychology, characters


class RomanceGenreModel(BaseGenreModel):

    @property
    def genre(self) -> str:
        return "romance"

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
        return f"""
## Romance Genre Model — Writing Rules

**Genre:** Romance ({subgenre or "General"})
**Arc:** {", ".join(config.RECOMMENDED_ARC_TYPES)}
**Chapter length:** {config.CHAPTER_LENGTH_WORDS[0]:,}-{config.CHAPTER_LENGTH_WORDS[1]:,} words

### The Non-Negotiables
1. **HEA is mandatory** — Happily Ever After must be earned and believable
2. **Meet by {int(config.MEET_POSITION * 100)}%** — leads must meet early
3. **First vulnerability by {int(config.FIRST_VULNERABILITY * 100)}%** — armor must crack
4. **Black moment at ~{int(config.BLACK_MOMENT_PCT * 100)}%** — relationship must appear truly doomed
5. **Max {config.SEPARATION_MAX} separations** — more = reader frustration
6. **The grovel is real** — when the hero wrongs the heroine, the apology must be genuine and specific
7. **Transformation must be earned** — no sudden personality changes

### Reader Psychology (Bowlby Attachment Theory)
Romance readers need: {", ".join(psychology.READER_CORE_NEEDS)}

### What Satisfies Romance Readers
{chr(10).join(f"- {k}: {v}" for k, v in psychology.SATISFACTION_TRIGGERS.items())}

### What Fails Romance Readers
{chr(10).join(f"- {k}" for k in psychology.DISSATISFACTION_TRIGGERS)}

### Black Moment Rules
The black moment MUST feel permanent. The reader should not see the solution.
Both characters must contribute to the break. It must arise from their character flaws, not external plot.

### Dialogue Style
- High dialogue ratio — romance is character-driven
- Subtext: characters rarely say what they mean when vulnerable
- Show love languages through action, not statement
- The hero expresses love through ACTS more than words (unless beta type)
"""

    def chapter_writing_instructions(self, bible, chapter_plan, scene_scores: list) -> str:
        position = getattr(chapter_plan, "position_pct", 0.5)
        target_emotions = getattr(chapter_plan, "target_emotions", config.TARGET_EMOTIONS)

        if position < 0.10:
            beat_guidance = "SETUP: Establish both leads' worlds and wounds. Plant the attraction seed."
        elif position < 0.25:
            beat_guidance = "MEET/EARLY: Leads meet. Chemistry established. Obstacle/conflict introduced."
        elif position < 0.45:
            beat_guidance = "BUILDING: Growing connection. Small vulnerabilities shared. Resistance still present."
        elif position < 0.60:
            beat_guidance = "MIDPOINT: Relationship deepens. Stakes raised. First real emotional risk taken."
        elif position < 0.78:
            beat_guidance = "COMPLICATION: Obstacle intensifies. Trust tested. Seeds of the black moment planted."
        elif position < 0.87:
            beat_guidance = "BLACK MOMENT: Relationship shatters. Both characters at their lowest. No clear way back."
        elif position < 0.95:
            beat_guidance = "RESOLUTION: Transformation proven. The grovel (if needed). HEA moment."
        else:
            beat_guidance = "EPILOGUE: Earned happiness. Show the relationship thriving."

        return f"""
### Chapter {chapter_plan.number} — Romance Writing Instructions

**Position:** {position:.0%} through story
**Beat:** {beat_guidance}
**Target emotions:** {", ".join(f"{k} {v:.0%}" for k, v in target_emotions.items() if v > 0.3)}
**Word count:** {getattr(chapter_plan, 'word_count_target', 3000):,} words

### This Chapter Must:
- Show (not tell) the emotional state of both leads
- Every scene of closeness must have a corresponding obstacle or cost
- Dialogue: characters should almost say what they feel — but deflect at the last moment
- End with either: deepened connection, raised stakes, or a question about the relationship
- The reader should FEEL the chemistry — not just be told about it

### Pacing:
- {int(config.SCENE_SEQUEL_RATIO * 100)}% scenes / {int((1-config.SCENE_SEQUEL_RATIO)*100)}% reflection
- After every high-tension scene: a moment of relief/connection
- Intimacy escalation must be gradual — emotional before physical
"""

    def character_building_prompt(self, role: str, tier: int, subgenre: str = "") -> str:
        if role in ("hero", "male_lead"):
            arch_dict = characters.HERO_ARCHETYPES
            arch_key = "alpha"
            if "beta" in subgenre.lower():
                arch_key = "beta"
            arch = arch_dict[arch_key]
        elif role in ("heroine", "female_lead"):
            arch_dict = characters.HEROINE_ARCHETYPES
            arch = arch_dict.get("independent")
        else:
            return (
                f"Create a {role} character for romance fiction (Tier {tier}). "
                f"Give them a clear function in the romantic conflict or support system."
            )

        if tier == 3:
            return f"Create a minor romance character: {role}. 3-5 specific traits. One memorable detail."

        ghost_options = "\n".join(f"  - {g}" for g in arch.get("ghost_templates", []))

        return f"""Create a Tier {tier} romance character with role: {role}

**Enneagram:** {arch.get("enneagram", "")}
**MBTI:** {arch.get("mbti", "")}
**Speech pattern:** {arch.get("speech_pattern", "")}
**Ghost/Wound (choose or invent):**
{ghost_options}

**Lie they carry:** {arch.get("lie", "")}
**Need (what they must learn):** {arch.get("need", "")}
**Arc:** {arch.get("arc", "Transformation through love")}

Build this character with:
- A specific backstory that caused their ghost (not generic trauma)
- A distinctive way of deflecting when vulnerable
- At least one relationship from their past that shaped their lie
- Their love language (how they show AND receive love)"""

    def validate_story_rules(self, bible) -> list[str]:
        violations = []
        if not bible.chapters:
            return violations

        total_planned = len(bible.chapter_plan) or 0
        last_ch = bible.chapters[-1]
        ch_num = last_ch.get("number", 0)

        # HEA only applies to the actual final chapter of the story
        if total_planned and ch_num >= total_planned:
            content = last_ch.get("content", "").lower()
            hea_signals = ["together", "love", "happy", "forever", "married", "home", "प्यार", "साथ", "खुश"]
            if not any(s in content for s in hea_signals):
                violations.append(
                    "Final chapter may be missing HEA — check for resolution of relationship."
                )

        tier1 = [c for c in bible.characters.values() if c.tier == 1]
        if len(tier1) < 2:
            violations.append(f"Only {len(tier1)} Tier 1 character(s). Romance needs hero + heroine.")

        return violations

    def suggest_chapter_emotions(self, position_pct: float, arc_type: str) -> dict:
        if position_pct < 0.15:
            return {"anticipation": 0.65, "joy": 0.50, "trust": 0.40}
        elif position_pct < 0.40:
            return {"joy": 0.70, "trust": 0.60, "anticipation": 0.65, "fear": 0.25}
        elif position_pct < 0.60:
            return {"joy": 0.65, "trust": 0.65, "anticipation": 0.60, "anger": 0.30}
        elif position_pct < 0.80:
            return {"anticipation": 0.70, "fear": 0.45, "anger": 0.50, "sadness": 0.40}
        elif position_pct < 0.88:
            return {"sadness": 0.80, "fear": 0.60, "anger": 0.50, "anticipation": 0.55}
        else:
            return {"joy": 0.90, "trust": 0.85, "anticipation": 0.50}

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
        if any(k in p for k in ["enemies", "hate", "rivalry", "forced", "antagonist"]):
            return "Enemies-to-Lovers"
        if any(k in p for k in ["second chance", "ex", "reunion", "past", "return"]):
            return "Second-Chance"
        if any(k in p for k in ["forbidden", "forbidden", "can't be", "shouldn't", "wrong"]):
            return "Forbidden Love"
        if any(k in p for k in ["historical", "regency", "victorian", "medieval", "century"]):
            return "Historical"
        if any(k in p for k in ["vampire", "werewolf", "paranormal", "magic", "shifter", "fae"]):
            return "Paranormal"
        return "Contemporary"
