"""
genres/literary/writer.py — Literary genre model.
"""

from genres.base_genre import BaseGenreModel
from genres.literary import config, psychology, characters


class LiteraryGenreModel(BaseGenreModel):

    @property
    def genre(self) -> str:
        return "literary"

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
## Literary Genre Model — Writing Rules

**Genre:** Literary Fiction ({subgenre or "General"})
**Arc:** {", ".join(config.RECOMMENDED_ARC_TYPES)}
**Chapter length:** {config.CHAPTER_LENGTH_WORDS[0]:,}-{config.CHAPTER_LENGTH_WORDS[1]:,} words
**Quality threshold: {config.QUALITY_THRESHOLD}** (highest bar — language is the experience)

### Core Principle: Language IS the Experience
In literary fiction, HOW something is said matters as much as WHAT is said.
Every sentence should be the best version of itself.
Beauty of language is not ornament — it is content.

### Theory of Mind (Kidd & Castano, 2013)
Literary fiction improves Theory of Mind. The reader EXERCISES empathy.
Every scene should give the reader access to inner states they couldn't otherwise experience.

### Subtext Principle (Hemingway Iceberg)
90% below the surface. Characters say one thing, mean another, reveal a third.
What is NOT said carries equal weight to what is said.
Use: action, object, environment to express what characters cannot say directly.

### Reader Psychology
Literary readers need: {", ".join(psychology.READER_CORE_NEEDS)}

### What Satisfies Literary Readers
{chr(10).join(f"- {k}: {v}" for k, v in psychology.SATISFACTION_TRIGGERS.items())}

### What Fails Literary Readers
{chr(10).join(f"- {k}" for k in psychology.DISSATISFACTION_TRIGGERS)}

### Epiphany (Joyce)
Required position: {int(config.EPIPHANY_PCT[0]*100)}-{int(config.EPIPHANY_PCT[1]*100)}% through story.
Must be EARNED through accumulated detail. Never stated directly.
Reader arrives at the epiphany WITH the character — not told about it.

### Ambiguity is Allowed
Resolution can be unresolved if the ambiguity is MEANINGFUL (not lazy).
False resolution — wrapping up everything neatly — feels dishonest.
"""

    def chapter_writing_instructions(self, bible, chapter_plan, scene_scores: list) -> str:
        position = getattr(chapter_plan, "position_pct", 0.5)
        target_emotions = getattr(chapter_plan, "target_emotions", config.TARGET_EMOTIONS)

        if position < 0.15:
            beat_guidance = "OPENING: Establish the character's inner world and outward situation. One perfect sensory detail that contains everything."
        elif position < 0.35:
            beat_guidance = "EARLY: Complicate the character's self-understanding. Introduce the central tension between who they are and who they think they are."
        elif position < 0.55:
            beat_guidance = "MIDDLE: The pressure builds. The lie becomes harder to maintain. Other characters reveal what the protagonist cannot see about themselves."
        elif position < 0.72:
            beat_guidance = "LATE MIDDLE: The character is most wrong about themselves. Or most isolated. Or most certain — just before everything changes."
        elif position < 0.90:
            beat_guidance = "EPIPHANY ZONE: The truth accumulates to the point where the character cannot avoid it. The moment of recognition — not stated, but felt."
        else:
            beat_guidance = "ENDING: The character changed (or didn't). The world changed (or didn't). The ending image echoes the opening — transformed."

        return f"""
### Chapter {chapter_plan.number} — Literary Fiction Writing Instructions

**Position:** {position:.0%} through story
**Beat:** {beat_guidance}
**Target emotions:** {", ".join(f"{k} {v:.0%}" for k, v in target_emotions.items() if v > 0.2)}
**Word count:** {getattr(chapter_plan, 'word_count_target', 4000):,} words

### This Chapter Must:
- Prioritize inner life: the character's perception of events matters more than the events
- One concrete sensory detail per key moment — not adjective lists, a single perfect specific
- Dialogue with subtext: characters almost say what they mean
- End with either: a shift in the character's understanding, or a moment that deepens the central irony
- The prose itself should carry emotional weight — not just describe emotion

### Sentence-level guidance:
- Vary sentence length: long for interiority/reflection, short for revelation
- Avoid adverbs — the verb should carry its own weight
- Avoid stated emotion ("she felt sad") — show the sensory/behavioral equivalent
- Every paragraph should earn its place

### What NOT to do:
- Do not explain the subtext
- Do not resolve ambiguity prematurely
- Do not prioritize plot momentum over character truth
"""

    def character_building_prompt(self, role: str, tier: int, subgenre: str = "") -> str:
        if tier == 3:
            return (
                f"Create a minor literary fiction character: {role}. "
                f"One specific trait that reveals something about the world or the protagonist. "
                f"No generic details."
            )

        arch = characters.COMPLEX_PROTAGONIST

        ghost_opts = "\n".join(f"  - {g}" for g in arch.get("ghost_templates", []))

        return f"""Create a Tier {tier} literary fiction character with role: {role}

**Enneagram:** {arch.get("enneagram", "")}
**MBTI:** {arch.get("mbti", "")}
**Speech pattern:** {arch.get("speech_pattern", "")}
**Arc types available:** {", ".join(arch.get("arc_types", ["positive", "negative", "flat"]))}

**Ghost/Wound options:**
{ghost_opts}

**Lie:** {arch.get("lie", "Specific to this character — not a generic archetype")}
**Need:** {arch.get("need", "")}

**Critical rule:** {arch.get("rule", "")}

Build with:
- A specific sensory memory that defines their wound (one image, not a paragraph)
- A specific way they deflect from truth (humor, intellectualism, anger, silence)
- A contradiction in their behavior that they cannot see about themselves
- One object, place, or recurring sensory detail that carries their emotional truth
- How they speak when at ease vs when threatened — the difference reveals character"""

    def validate_story_rules(self, bible) -> list[str]:
        violations = []

        # Literary needs deep character, not many
        tier1 = [c for c in bible.characters.values() if c.tier == 1]
        if not tier1:
            violations.append("No Tier 1 character. Literary fiction requires at least one deeply developed protagonist.")

        protagonist = tier1[0] if tier1 else None
        if protagonist and not protagonist.ghost:
            violations.append(
                f"Protagonist '{protagonist.name}' has no Ghost/Wound. "
                f"Literary fiction is driven by the character's inner wound."
            )

        return violations

    def suggest_chapter_emotions(self, position_pct: float, arc_type: str) -> dict:
        if position_pct < 0.15:
            return {"trust": 0.50, "sadness": 0.35, "anticipation": 0.40}
        elif position_pct < 0.35:
            return {"sadness": 0.45, "anticipation": 0.40, "fear": 0.30, "trust": 0.40}
        elif position_pct < 0.60:
            return {"sadness": 0.50, "fear": 0.40, "anger": 0.35, "anticipation": 0.35}
        elif position_pct < 0.75:
            return {"sadness": 0.55, "fear": 0.45, "disgust": 0.30, "anger": 0.35}
        elif position_pct < 0.90:
            return {"sadness": 0.60, "surprise": 0.50, "trust": 0.45, "anticipation": 0.40}
        else:
            return {"trust": 0.55, "sadness": 0.45, "joy": 0.40, "surprise": 0.35}

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
        if any(k in p for k in ["magical realism", "magic realism", "marquez", "borges"]):
            return "Magical Realism"
        if any(k in p for k in ["psychological", "unreliable", "perception", "mind"]):
            return "Psychological"
        if any(k in p for k in ["historical", "period", "century", "war", "revolution"]):
            return "Historical Literary"
        if any(k in p for k in ["social", "class", "race", "society", "political", "systemic"]):
            return "Social Commentary"
        return "Character Study"
