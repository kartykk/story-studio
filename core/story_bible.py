"""
core/story_bible.py — Complete persistent memory for a story.

Extended from v1 with:
- 3-tier character system (Tier 1: full 200+ fields, Tier 2: 50-100, Tier 3: 3-5)
- Enneagram + MBTI + Big Five OCEAN personality frameworks
- Vogler 8 archetypes
- Language selection (Stage 0)
- Emotional arc type per story
- Scene draft stage (Stage 6b)
- SceneInterestScore references per ChapterPlan

Stages filled in order:
  0. language       → language + language_code selection
  1. premise        → one-sentence concept + logline + theme
  2. title          → 5 options generated, one chosen
  3. world          → geography, culture, history, politics, magic/tech, religion
  4. characters     → full psychological profile per character
  5. beats          → Save the Cat 15-beat structure
  6. chapter_plan   → chapter-by-chapter outline
  6b. scene_drafts  → brief scene outlines per chapter (approved before full writing)
  7. chapters       → actual written content
  8. messages       → full Claude conversation history (never trimmed)
"""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


STORIES_DIR = Path(__file__).parent.parent / "stories"


# ── Tier System ───────────────────────────────────────────────────────────────

CHARACTER_TIERS = {
    1: "Protagonist / Antagonist — Full 200+ field psychological profile",
    2: "Supporting — Compact 50-100 field profile",
    3: "Minor — 3-5 trait description only",
}

VOGLER_ARCHETYPES = [
    "Hero", "Mentor", "Threshold Guardian", "Herald",
    "Shapeshifter", "Shadow", "Ally", "Trickster",
]

ENNEAGRAM_TYPES = [
    "Type 1 (Reformer)", "Type 2 (Helper)", "Type 3 (Achiever)",
    "Type 4 (Individualist)", "Type 5 (Investigator)", "Type 6 (Loyalist)",
    "Type 7 (Enthusiast)", "Type 8 (Challenger)", "Type 9 (Peacemaker)",
]

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]


# ── Character Profile ─────────────────────────────────────────────────────────

@dataclass
class CharacterProfile:
    # ── Identity ──
    name: str = ""
    role: str = ""               # protagonist / antagonist / mentor / ally / etc.
    age: str = ""
    physical_description: str = ""
    speech_pattern: str = ""     # accent, vocabulary, rhythm, distinctive phrases

    # ── Tier ──
    tier: int = 2                # 1 = Tier 1 full, 2 = supporting, 3 = minor
    is_pov_character: bool = False

    # ── Psychology (K.M. Weiland Ghost/Lie/Want/Need) ──
    ghost: str = ""              # backstory wound/trauma
    lie: str = ""                # misbelief carried because of the ghost
    want: str = ""               # external goal
    need: str = ""               # internal truth they must learn

    # ── Character makeup ──
    flaw: str = ""
    strength: str = ""
    arc_type: str = ""           # positive / negative / flat
    arc_summary: str = ""

    # ── Personality Frameworks (Tier 1 only) ──
    vogler_archetype: str = ""       # Hero, Shadow, Mentor, etc.
    enneagram_type: str = ""         # e.g. "Type 8 (Challenger)"
    mbti_type: str = ""              # e.g. "INTJ"
    ocean_scores: dict = field(default_factory=dict)  # {O, C, E, A, N} each 0.0-1.0

    # ── Relationships ──
    relationships: dict = field(default_factory=dict)  # {char_name: relationship_desc}

    # ── Voice (ElevenLabs) ──
    voice_id: str = ""
    voice_name: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterProfile":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def prompt_summary(self) -> str:
        """Compact summary for Claude's system prompt."""
        if self.tier == 3:
            return f"**{self.name}** ({self.role}): {self.flaw or self.speech_pattern}"

        lines = [
            f"**{self.name}** ({self.role}, {self.age}) [Tier {self.tier}]",
            f"  Ghost/Wound: {self.ghost}",
            f"  Lie they believe: {self.lie}",
            f"  Want (external): {self.want}",
            f"  Need (internal): {self.need}",
            f"  Flaw: {self.flaw} | Strength: {self.strength}",
            f"  Arc: {self.arc_type} — {self.arc_summary}",
            f"  Voice/Speech: {self.speech_pattern}",
        ]
        if self.tier == 1 and self.vogler_archetype:
            lines.append(
                f"  Vogler: {self.vogler_archetype} | "
                f"Enneagram: {self.enneagram_type} | MBTI: {self.mbti_type}"
            )
        return "\n".join(lines)


# ── Save the Cat Beat ─────────────────────────────────────────────────────────

@dataclass
class StoryBeat:
    number: int = 0
    name: str = ""
    description: str = ""
    act: str = ""
    chapter_hint: str = ""


BEAT_NAMES = [
    (1,  "Opening Image",      "Act I"),
    (2,  "Theme Stated",       "Act I"),
    (3,  "Set-Up",             "Act I"),
    (4,  "Catalyst",           "Act I"),
    (5,  "Debate",             "Act I"),
    (6,  "Break into Two",     "Act I"),
    (7,  "B Story",            "Act II"),
    (8,  "Fun and Games",      "Act II"),
    (9,  "Midpoint",           "Act II"),
    (10, "Bad Guys Close In",  "Act II"),
    (11, "All Is Lost",        "Act II"),
    (12, "Dark Night of Soul", "Act II"),
    (13, "Break into Three",   "Act III"),
    (14, "Finale",             "Act III"),
    (15, "Final Image",        "Act III"),
]


# ── Scene Draft (Stage 6b) ────────────────────────────────────────────────────

@dataclass
class SceneDraft:
    scene_number: int = 0
    beats_covered: list = field(default_factory=list)
    pov_character: str = ""
    location: str = ""
    brief_description: str = ""       # 2-4 sentence outline
    emotional_goal: str = ""
    target_emotions: dict = field(default_factory=dict)   # {emotion: 0.0-1.0}
    sis_estimate: float = 50.0        # Scene Interest Score estimate before writing
    word_count_target: int = 1500
    narrative_mode: str = "Scene"
    approved: bool = False            # user must approve before full writing

    def to_dict(self) -> dict:
        return asdict(self)


# ── Chapter Plan ──────────────────────────────────────────────────────────────

@dataclass
class ChapterPlan:
    number: int = 0
    title: str = ""
    beats_covered: list = field(default_factory=list)
    pov_character: str = ""
    location: str = ""
    summary: str = ""
    emotional_goal: str = ""

    # Extended fields
    arc_type: str = ""                 # Reagan arc type for this chapter
    target_emotion_intensity: float = 0.5
    target_emotions: dict = field(default_factory=dict)
    position_pct: float = 0.0         # 0.0-1.0 story position

    # Scene breakdown
    scenes: list = field(default_factory=list)         # list of SceneDraft dicts
    scene_interest_scores: list = field(default_factory=list)  # list of SIS floats
    draft_approved: bool = False       # scene drafts approved before writing

    # Output
    word_count_target: int = 2000

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ChapterPlan":
        allowed = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in allowed})


# ── World Bible ───────────────────────────────────────────────────────────────

@dataclass
class WorldBible:
    overview: str = ""
    geography: str = ""
    history: str = ""
    culture: str = ""
    politics: str = ""
    economy: str = ""
    religion: str = ""
    magic_or_tech: str = ""
    language: str = ""
    unique_elements: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorldBible":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def prompt_summary(self) -> str:
        parts = []
        for attr, label in [
            ("overview", "World Overview"),
            ("geography", "Geography"),
            ("history", "History"),
            ("culture", "Culture"),
            ("politics", "Politics"),
            ("economy", "Economy"),
            ("religion", "Religion"),
            ("magic_or_tech", "Magic/Technology"),
            ("unique_elements", "Unique Elements"),
        ]:
            val = getattr(self, attr)
            if val:
                parts.append(f"**{label}:** {val}")
        return "\n\n".join(parts)


# ── Story Bible (main container) ──────────────────────────────────────────────

class StoryBible:
    def __init__(self, story_id: str):
        self.story_id = story_id
        self.path = STORIES_DIR / f"{story_id}.json"

        # Stage 0: Language
        self.language: str = "English"
        self.language_code: str = "en"

        # Stage 1: Premise
        self.premise: str = ""
        self.logline: str = ""
        self.theme: str = ""
        self.genre: str = ""
        self.genre_model_name: str = ""    # "crime", "romance", etc.
        self.target_audience: str = ""
        self.tone: str = ""

        # Stage 2: Title
        self.title: str = ""
        self.title_candidates: list[str] = []

        # Stage 3: World
        self.world: WorldBible = WorldBible()

        # Stage 4: Characters
        self.characters: dict[str, CharacterProfile] = {}

        # Stage 5: Beats
        self.beats: list[StoryBeat] = []

        # Stage 6: Chapter Plan
        self.chapter_plan: list[ChapterPlan] = []

        # Emotional arc
        self.emotional_arc_type: str = "Man in Hole"   # Reagan arc type

        # Suggested character breakdown (set by genre model)
        self.suggested_character_breakdown: dict = {}

        # Stage 7: Written Chapters
        self.chapters: list[dict] = []

        # Stage 8: Message history
        self.messages: list[dict] = []

        # Narrator voice
        self.narrator_voice_id: str = ""
        self.narrator_voice_name: str = ""

        # Metadata
        self.stage_complete: dict[str, bool] = {
            "language": False,
            "premise": False,
            "title": False,
            "world": False,
            "characters": False,
            "beats": False,
            "chapter_plan": False,
            "scene_drafts": False,
        }
        self.created_at: str = datetime.now().isoformat()
        self.updated_at: str = datetime.now().isoformat()

    # ── Characters ──

    def add_character(self, char: CharacterProfile):
        self.characters[char.name.lower()] = char

    def get_character(self, name: str) -> Optional[CharacterProfile]:
        return self.characters.get(name.lower()) or self.characters.get(name.lower().split()[0])

    def get_tier1_characters(self) -> list[CharacterProfile]:
        return [c for c in self.characters.values() if c.tier == 1]

    def get_pov_characters(self) -> list[CharacterProfile]:
        return [c for c in self.characters.values() if c.is_pov_character]

    def character_list_for_prompt(self) -> str:
        if not self.characters:
            return "No characters defined yet."
        # Tier 1 first, then Tier 2, then Tier 3
        sorted_chars = sorted(self.characters.values(), key=lambda c: c.tier)
        return "\n\n".join(c.prompt_summary() for c in sorted_chars)

    def character_compact_list(self) -> str:
        """Compact single-line list for scoring prompts."""
        lines = []
        for c in sorted(self.characters.values(), key=lambda c: c.tier):
            lines.append(f"{c.name} ({c.role}): {c.want[:80]}")
        return "\n".join(lines)

    # ── Beats ──

    def beats_for_prompt(self) -> str:
        if not self.beats:
            return "No beats defined yet."
        return "\n".join(f"Beat {b.number} — {b.name} ({b.act}): {b.description}" for b in self.beats)

    # ── Chapter Plan ──

    def chapter_plan_for_prompt(self) -> str:
        if not self.chapter_plan:
            return "No chapter plan yet."
        lines = []
        for cp in self.chapter_plan:
            beats_str = ", ".join(f"Beat {n}" for n in cp.beats_covered)
            lines.append(
                f"Chapter {cp.number}: '{cp.title}' — {cp.summary}\n"
                f"  POV: {cp.pov_character} | Location: {cp.location} | Beats: {beats_str}\n"
                f"  Emotional goal: {cp.emotional_goal} | Target intensity: {cp.target_emotion_intensity:.0%}"
            )
        return "\n\n".join(lines)

    def get_chapter_plan(self, number: int) -> Optional[ChapterPlan]:
        return next((cp for cp in self.chapter_plan if cp.number == number), None)

    # ── Messages ──

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    # ── Chapters ──

    def chapters_written_summary(self) -> str:
        if not self.chapters:
            return "None written yet."
        return "\n".join(f"Chapter {c['number']}: {c['title']}" for c in self.chapters)

    def add_chapter(self, number: int, title: str, content: str):
        existing = next((c for c in self.chapters if c["number"] == number), None)
        if existing:
            existing["content"] = content
            existing["title"] = title
        else:
            self.chapters.append({"number": number, "title": title, "content": content})

    def get_chapter(self, number: int) -> Optional[dict]:
        return next((c for c in self.chapters if c["number"] == number), None)

    # ── Serialization ──

    def save(self):
        STORIES_DIR.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now().isoformat()
        data = {
            "story_id":                    self.story_id,
            "language":                    self.language,
            "language_code":               self.language_code,
            "premise":                     self.premise,
            "logline":                     self.logline,
            "theme":                       self.theme,
            "genre":                       self.genre,
            "genre_model_name":            self.genre_model_name,
            "target_audience":             self.target_audience,
            "tone":                        self.tone,
            "title":                       self.title,
            "title_candidates":            self.title_candidates,
            "world":                       self.world.to_dict(),
            "characters":                  {k: v.to_dict() for k, v in self.characters.items()},
            "beats":                       [asdict(b) for b in self.beats],
            "chapter_plan":                [cp.to_dict() for cp in self.chapter_plan],
            "emotional_arc_type":          self.emotional_arc_type,
            "suggested_character_breakdown": self.suggested_character_breakdown,
            "chapters":                    self.chapters,
            "messages":                    self.messages,
            "narrator_voice_id":           self.narrator_voice_id,
            "narrator_voice_name":         self.narrator_voice_name,
            "stage_complete":              self.stage_complete,
            "created_at":                  self.created_at,
            "updated_at":                  self.updated_at,
        }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, story_id: str) -> "StoryBible":
        path = STORIES_DIR / f"{story_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Story '{story_id}' not found.")
        with open(path) as f:
            data = json.load(f)

        bible = cls(story_id)
        bible.language           = data.get("language", "English")
        bible.language_code      = data.get("language_code", "en")
        bible.premise            = data.get("premise", "")
        bible.logline            = data.get("logline", "")
        bible.theme              = data.get("theme", "")
        bible.genre              = data.get("genre", "")
        bible.genre_model_name   = data.get("genre_model_name", "")
        bible.target_audience    = data.get("target_audience", "")
        bible.tone               = data.get("tone", "")
        bible.title              = data.get("title", "")
        bible.title_candidates   = data.get("title_candidates", [])
        bible.world              = WorldBible.from_dict(data.get("world", {}))
        bible.characters         = {
            k: CharacterProfile.from_dict(v)
            for k, v in data.get("characters", {}).items()
        }
        bible.beats              = [StoryBeat(**b) for b in data.get("beats", [])]
        bible.chapter_plan       = [ChapterPlan.from_dict(cp) for cp in data.get("chapter_plan", [])]
        bible.emotional_arc_type = data.get("emotional_arc_type", "Man in Hole")
        bible.suggested_character_breakdown = data.get("suggested_character_breakdown", {})
        bible.chapters           = data.get("chapters", [])
        bible.messages           = data.get("messages", [])
        bible.narrator_voice_id  = data.get("narrator_voice_id", "")
        bible.narrator_voice_name = data.get("narrator_voice_name", "")

        # Backward compat: merge old stage_complete with new keys
        old_stages = data.get("stage_complete", {})
        for key in bible.stage_complete:
            bible.stage_complete[key] = old_stages.get(key, False)

        bible.created_at = data.get("created_at", "")
        bible.updated_at = data.get("updated_at", "")
        return bible

    @classmethod
    def list_stories(cls) -> list[str]:
        STORIES_DIR.mkdir(parents=True, exist_ok=True)
        return [
            f.stem for f in sorted(STORIES_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime, reverse=True)
        ]

    @classmethod
    def exists(cls, story_id: str) -> bool:
        return (STORIES_DIR / f"{story_id}.json").exists()
