"""
genres/base_genre.py — Abstract base class for all 5 genre models.

Every genre model (Crime, Romance, Horror, Fantasy, Literary) inherits this.
Forces each to implement the same interface so main.py can route to any
genre transparently.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseGenreModel(ABC):
    """Abstract base class. All 5 genre models must implement every method."""

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def genre(self) -> str:
        """Genre name: 'crime', 'romance', 'horror', 'fantasy', 'literary'"""

    @property
    @abstractmethod
    def subgenres(self) -> list[str]:
        """List of subgenres this model handles."""

    @property
    @abstractmethod
    def recommended_arc_types(self) -> list[str]:
        """Reagan arc types ordered by fit for this genre."""

    @property
    @abstractmethod
    def quality_threshold(self) -> int:
        """Minimum quality score (0-100) required to pass the quality gate."""

    @property
    @abstractmethod
    def chapter_length_range(self) -> tuple[int, int]:
        """(min_words, max_words) per chapter."""

    # ── Claude Prompt Extensions ──────────────────────────────────────────────

    @abstractmethod
    def system_prompt_addon(self, bible) -> str:
        """
        Genre-specific text injected into every Claude system prompt.
        Should include: genre conventions, pacing rules, key research numbers,
        what to optimize for, what to avoid.
        """

    @abstractmethod
    def chapter_writing_instructions(self, bible, chapter_plan, scene_scores: list) -> str:
        """
        Genre-specific instructions for writing one chapter.
        Injected after the base writing prompt.

        Args:
            bible: StoryBible
            chapter_plan: ChapterPlan for this chapter
            scene_scores: list of SceneInterestScore for this chapter's scenes
        """

    @abstractmethod
    def character_building_prompt(self, role: str, tier: int, subgenre: str = "") -> str:
        """
        Genre-specific character building prompt for Claude.
        Used in the character stage to build psychologically authentic characters.

        Args:
            role: character role (protagonist, antagonist, etc.)
            tier: 1 = full profile, 2 = supporting, 3 = minor
            subgenre: optional subgenre for more specific archetypes
        """

    @abstractmethod
    def validate_story_rules(self, bible) -> list[str]:
        """
        Check genre rules are followed.
        Returns list of violations (empty = all good).
        Called before finalizing each chapter.
        """

    @abstractmethod
    def suggest_chapter_emotions(self, position_pct: float, arc_type: str) -> dict:
        """
        Return target emotion dict for a chapter at this story position.
        Used by interest_scorer and quality_gate.

        Args:
            position_pct: 0.0-1.0 (chapter position in story)
            arc_type: Reagan arc type

        Returns:
            dict like {"fear": 0.75, "anticipation": 0.65}
        """

    @abstractmethod
    def get_reader_psychology(self) -> dict:
        """
        Reader psychology profile for this genre.
        Used to calibrate what to optimize for.

        Returns:
            dict with keys: core_needs, satisfaction_triggers, dissatisfaction_triggers,
                            suspense_weights
        """

    # ── Optional Overrides ────────────────────────────────────────────────────

    def chapter_word_count(self, sis: float, position_pct: float = 0.5) -> int:
        """
        Return target word count from Scene Interest Score.
        Default implementation uses genre chapter_length_range.
        Override for genre-specific logic.
        """
        min_w, max_w = self.chapter_length_range
        # Scale by SIS: 0 SIS → min, 100 SIS → max
        return int(min_w + (max_w - min_w) * (sis / 100.0))

    def detect_subgenre(self, premise: str, tone: str = "") -> str:
        """
        Auto-detect subgenre from premise text.
        Default: return first subgenre. Override for smarter detection.
        """
        premise_lower = premise.lower()
        for sg in self.subgenres:
            if sg.lower() in premise_lower:
                return sg
        return self.subgenres[0] if self.subgenres else ""

    def world_building_prompt(self, subgenre: str = "") -> str:
        """
        Genre-specific world building instructions.
        Default: generic. Override for fantasy/sci-fi where world is critical.
        """
        return (
            f"Build a world appropriate for {self.genre} fiction. "
            f"Focus on the details that create atmosphere and conflict "
            f"specific to this genre. Include only what serves the story."
        )

    def suggested_character_count(self) -> dict:
        """
        Suggest how many characters of each tier to create.
        Returns dict like {"tier1": 2, "tier2": 3, "tier3": 4}
        """
        return {"tier1": 2, "tier2": 3, "tier3": 4}

    def genre_display_name(self) -> str:
        return self.genre.title()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} genre={self.genre}>"
