"""
genres/horror/writer.py — Horror genre model.
"""

from genres.base_genre import BaseGenreModel
from genres.horror import config, psychology, characters


class HorrorGenreModel(BaseGenreModel):

    @property
    def genre(self) -> str:
        return "horror"

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
## Horror Genre Model — Writing Rules

**Genre:** Horror ({subgenre or "General"})
**Arc:** {", ".join(config.RECOMMENDED_ARC_TYPES)}
**Chapter length:** {config.CHAPTER_LENGTH_WORDS[0]:,}-{config.CHAPTER_LENGTH_WORDS[1]:,} words

### The Three-Stage Fear Model
1. **DREAD ({int(config.DREAD_PHASE[0]*100)}-{int(config.DREAD_PHASE[1]*100)}% of buildup):** Unknown threat. Imagination fills the blanks. DO NOT show the monster yet.
2. **TERROR:** Threat revealed after sustained dread. The buildup makes it hit harder.
3. **HORROR:** Emotional aftermath. Processing time before the next cycle.

### Excitation Transfer Theory (Zillmann & Tamborini)
Fear intensity converts to euphoria when the threat resolves.
Enjoyment is proportional to the buildup intensity.
The reader's imagination ALWAYS exceeds description — exploit this.

### Mandatory Rules
1. **Humanize victims BEFORE {int(config.VICTIM_DEVELOPMENT_PCT*100)}%** — reader must care before horror strikes
2. **DO NOT show the monster before {int(config.MONSTER_PARTIAL_REVEAL*100)}%** — dread requires mystery
3. **{config.FALSE_SCARE_COUNT[0]}-{config.FALSE_SCARE_COUNT[1]} false scares** — fewer = insufficient priming; more = numbness
4. **First false scare before {int(config.FIRST_FALSE_SCARE_PCT*100)}%** — establish the possibility of danger early
5. **Monster has purpose** — random evil is less frightening than purposeful evil

### What Satisfies Horror Readers
{chr(10).join(f"- {k}: {v}" for k, v in psychology.SATISFACTION_TRIGGERS.items())}

### What Fails Horror Readers
{chr(10).join(f"- {k}" for k in psychology.DISSATISFACTION_TRIGGERS)}

### Atmosphere Rules
- Sensory detail: prioritize SOUND and SMELL over sight (more primal fear responses)
- Make the familiar slightly wrong — uncanny valley is more effective than the overtly monstrous
- Establish safety, then violate it
- Isolate before threatening — cut off help before the threat arrives
- Subgenre note: {subgenre_cfg.get("atmosphere", "Build dread through specificity, not quantity of scares")}
"""

    def chapter_writing_instructions(self, bible, chapter_plan, scene_scores: list) -> str:
        position = getattr(chapter_plan, "position_pct", 0.5)
        target_emotions = getattr(chapter_plan, "target_emotions", config.TARGET_EMOTIONS)

        if position < 0.12:
            beat_guidance = "SETUP: Establish the world, the characters, the sense of normalcy. Hint at wrongness — one detail that shouldn't be there."
        elif position < 0.25:
            beat_guidance = "FIRST SCARE: Cat scare establishes possibility. False alarm. But reader now knows danger is possible."
        elif position < 0.45:
            beat_guidance = "DREAD PHASE: Systematic buildup. Glimpses. Sounds. Missing time. DO NOT show the threat fully."
        elif position < 0.65:
            beat_guidance = "PARTIAL REVEAL: The threat is glimpsed. Still not fully understood. Terror begins."
        elif position < 0.85:
            beat_guidance = "ESCALATION: Threat is real and known. Characters are losing. Darkest point approaches."
        else:
            beat_guidance = "CLIMAX/RESOLUTION: Confrontation. Survival or defeat. Catharsis."

        return f"""
### Chapter {chapter_plan.number} — Horror Writing Instructions

**Position:** {position:.0%} through story
**Beat:** {beat_guidance}
**Target emotions:** {", ".join(f"{k} {v:.0%}" for k, v in target_emotions.items() if v > 0.3)}
**Word count:** {getattr(chapter_plan, 'word_count_target', 2500):,} words

### This Chapter Must:
- Use sensory detail (sound, smell, texture) to build atmosphere
- Never explain the horror directly — imply, suggest, obscure
- End with either: a scare paid off, a scare introduced but unresolved, or safety violated
- Increase isolation — remove one more escape route or support
- The reader should feel watched even when nothing is shown

### Pacing:
- Slow build → sudden burst → brief recovery → slow build again
- DO NOT sustain maximum fear — let the reader breathe so the next scare lands harder
- Long sentences for dread; short, chopped sentences for the terror moment
"""

    def character_building_prompt(self, role: str, tier: int, subgenre: str = "") -> str:
        if role in ("protagonist", "final_girl", "survivor"):
            arch = characters.FINAL_GIRL_ARCHETYPE
        elif role in ("antagonist", "monster", "villain"):
            arch = characters.MONSTER_ARCHETYPE
        elif role == "victim":
            arch = characters.VICTIM_ARCHETYPE
        else:
            arch = characters.SKEPTIC_ARCHETYPE

        if tier == 3:
            return (
                f"Create a minor horror character: {role}. "
                f"One specific trait that makes them sympathetic before they face danger. "
                f"One concrete detail (a dream, a relationship, a fear)."
            )

        ghost_opts = "\n".join(f"  - {g}" for g in arch.get("ghost_templates", []))

        return f"""Create a Tier {tier} horror character with role: {role}

**Vogler archetype:** {arch.get("vogler_archetype", "")}
**Enneagram:** {arch.get("enneagram", "")}
**Speech pattern:** {arch.get("speech_pattern", "")}
**Arc:** {arch.get("arc", "")}

**Ghost/Wound:**
{ghost_opts}

**Lie:** {arch.get("lie", "")}
**Need:** {arch.get("need", "")}

**Critical rule:** {arch.get("modern_evolution", arch.get("rule", "Make them believable."))}
**Development timing:** {arch.get("development_timing", "Establish before danger arrives.")}

Build this character with: one specific fear, one named relationship, one concrete hope or goal.
Horror works because we fear for specific people — not archetypes."""

    def validate_story_rules(self, bible) -> list[str]:
        violations = []
        subgenre = getattr(bible, "subgenre", "")
        cfg = config.SUBGENRE_CONFIGS.get(subgenre, {})

        if cfg.get("cosmic_horror_resolved") is False and bible.chapters:
            last = bible.chapters[-1].get("content", "").lower()
            if "resolved" in last or "destroyed" in last or "safe" in last:
                violations.append(
                    "Cosmic Horror cannot be resolved — the final chapter implies resolution. "
                    "Cosmic horror ends in defeat, madness, or continuation of the threat."
                )

        tier1 = [c for c in bible.characters.values() if c.tier == 1]
        if len(tier1) < 1:
            violations.append("No Tier 1 character. Horror needs at least a protagonist.")

        return violations

    def suggest_chapter_emotions(self, position_pct: float, arc_type: str) -> dict:
        if position_pct < 0.12:
            return {"anticipation": 0.40, "trust": 0.50, "joy": 0.30}
        elif position_pct < 0.25:
            return {"anticipation": 0.60, "fear": 0.40, "surprise": 0.50}
        elif position_pct < 0.45:
            return {"anticipation": 0.75, "fear": 0.60, "disgust": 0.35}
        elif position_pct < 0.65:
            return {"fear": 0.75, "anticipation": 0.70, "disgust": 0.50, "surprise": 0.60}
        elif position_pct < 0.85:
            return {"fear": 0.85, "anticipation": 0.70, "disgust": 0.55, "sadness": 0.40}
        else:
            return {"fear": 0.80, "sadness": 0.50, "surprise": 0.60, "disgust": 0.45}

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
        if any(k in p for k in ["psychological", "mind", "paranoia", "unreliable", "trauma"]):
            return "Psychological"
        if any(k in p for k in ["cosmic", "lovecraft", "eldritch", "ancient", "unknowable"]):
            return "Cosmic Horror"
        if any(k in p for k in ["body", "flesh", "mutation", "transform", "organic"]):
            return "Body Horror"
        if any(k in p for k in ["gothic", "castle", "manor", "victorian", "decay", "moor"]):
            return "Gothic"
        if any(k in p for k in ["slasher", "killer", "masked", "serial", "victims"]):
            return "Slasher"
        return "Supernatural"
