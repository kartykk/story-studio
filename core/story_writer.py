"""
core/story_writer.py — Claude API calls for every stage of the writing pipeline.

Upgraded from v1 with:
- Genre model integration (genre-specific prompts, pacing, emotion targets)
- Language selection support (Stage 0)
- Scene draft stage (Stage 6b)
- Quality-gated write_chapter() with auto-retry
- Tier-aware character building (Tier 1: 200+ fields, Tier 2: compact, Tier 3: brief)
- Emotion scoring per chapter via DeepSeek
- Scene Interest Score per chapter

Stages:
  0. select_language()      → language + language_code
  1. develop_premise()      → logline + theme + genre + tone + arc type
  2. generate_titles()      → 5 title options
  3. build_world()          → full world bible
  4. build_character()      → tier-aware psychological profile
  5. generate_beats()       → Save the Cat 15 beats
  6. plan_chapters()        → chapter outline with emotional targets
  6b. draft_chapter_scenes()→ scene-level outline per chapter (approved before writing)
  7. write_chapter()        → actual prose (quality-gated with auto-retry)
  8. refine_chapter()       → revision from feedback
  9. ask_question()         → any story question
"""

import json
import re
import os
import anthropic
from typing import Optional

from core.story_bible import (
    StoryBible, CharacterProfile, WorldBible,
    StoryBeat, ChapterPlan, SceneDraft, BEAT_NAMES
)
from core.arc_calculator import (
    assign_chapter_intensities, suggest_arc_type, ARC_DESCRIPTIONS
)
from core.interest_scorer import score_scene, allocate_word_counts, SceneInterestScore
from core.env import require_key


MODEL         = "claude-opus-4-6"
MODEL_FAST    = "claude-sonnet-4-6"
THINK_BUDGET  = 10000
MAX_API_MESSAGE_PAIRS = 8   # rolling window — full bible is in system prompt


# ── Client ────────────────────────────────────────────────────────────────────

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))


def _messages_for_api(bible: StoryBible, extra_user: Optional[str] = None) -> list[dict]:
    """Recent conversation window for API calls (avoids unbounded context growth)."""
    keep = MAX_API_MESSAGE_PAIRS * 2
    msgs = list(bible.messages[-keep:]) if bible.messages else []
    if extra_user:
        msgs = msgs + [{"role": "user", "content": extra_user}]
    return msgs


def _persist_approved_chapter(
    bible: StoryBible,
    chapter_number: int,
    chapter_text: str,
    title: str,
):
    """Save an approved chapter and a compact message pair (not every retry)."""
    bible.add_message(
        "user",
        f"Write Chapter {chapter_number}: \"{title}\" (approved after quality gate)",
    )
    bible.add_message("assistant", chapter_text)
    bible.add_chapter(chapter_number, title, chapter_text)
    bible.save()


def _try_repair_json(raw: str) -> "dict | list | None":
    """Best-effort repair for truncated or slightly malformed JSON."""
    raw = raw.strip()
    if not raw:
        return None

    attempts = [raw, raw.rstrip(", \n") + "}"]

    # Close unclosed braces/brackets
    for base in [raw, raw.rstrip(", \n")]:
        open_braces = base.count("{") - base.count("}")
        open_brackets = base.count("[") - base.count("]")
        suffix = "]" * max(0, open_brackets) + "}" * max(0, open_braces)
        if suffix:
            attempts.append(base.rstrip(", \n") + suffix)

    for candidate in attempts:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _extract_json(text: str) -> "dict | list":
    text = text.strip()

    # Fenced block — handle truncated responses missing closing ```
    if "```" in text:
        start = text.find("```")
        body_start = text.find("\n", start)
        if body_start >= 0:
            body_start += 1
            end = text.rfind("```")
            raw = text[body_start:end].strip() if end > body_start else text[body_start:].strip()
            if raw:
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    repaired = _try_repair_json(raw)
                    if repaired is not None:
                        return repaired

    match = re.search(r"(\{[\s\S]+\}|\[[\s\S]+\])", text)
    if match:
        raw = match.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            repaired = _try_repair_json(raw)
            if repaired is not None:
                return repaired

    repaired = _try_repair_json(text)
    if repaired is not None:
        return repaired

    raise ValueError(f"No JSON in response:\n{text[:500]}")


def _call_json(
    client: anthropic.Anthropic,
    model: str,
    prompt: str,
    max_tokens: int,
    retries: int = 2,
) -> "dict | list":
    """Call Claude and parse JSON with retry on parse failure."""
    last_error = None
    current_prompt = prompt

    for attempt in range(retries):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": current_prompt}],
        )
        raw = response.content[0].text
        try:
            return _extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            current_prompt = (
                prompt
                + "\n\nIMPORTANT: Your previous response was invalid or truncated JSON. "
                "Return ONLY complete valid JSON. Keep each string field concise (2-4 sentences). "
                "No markdown outside the JSON block."
            )

    raise ValueError(str(last_error))


# ── System Prompt ─────────────────────────────────────────────────────────────

def _system_prompt(bible: StoryBible, genre_model=None) -> str:
    """Full story bible as system prompt — passed every Claude call so it never forgets."""
    base = f"""You are a master story writer with deep knowledge of narrative craft, character psychology, and genre conventions.
Language: Write in {bible.language}.

═══════════════════════════════════════
STORY BIBLE
═══════════════════════════════════════

TITLE: {bible.title or "(untitled)"}
GENRE: {bible.genre}  |  TONE: {bible.tone}  |  AUDIENCE: {bible.target_audience}
EMOTIONAL ARC: {bible.emotional_arc_type}

LOGLINE:
{bible.logline}

THEME:
{bible.theme}

───────────────────────────────────────
WORLD
───────────────────────────────────────
{bible.world.prompt_summary() or "World not yet built."}

───────────────────────────────────────
CHARACTERS
───────────────────────────────────────
{bible.character_list_for_prompt()}

───────────────────────────────────────
SAVE THE CAT — 15 BEATS
───────────────────────────────────────
{bible.beats_for_prompt()}

───────────────────────────────────────
CHAPTER PLAN
───────────────────────────────────────
{bible.chapter_plan_for_prompt()}

───────────────────────────────────────
CHAPTERS WRITTEN SO FAR
───────────────────────────────────────
{bible.chapters_written_summary()}

═══════════════════════════════════════
WRITING RULES
═══════════════════════════════════════
- Write literary prose. No bullet points in story text.
- Dialogue: "Text," Character said. / Character said, "Text."
- Always attribute dialogue clearly.
- Scene breaks: ---
- Chapter header: # Chapter [N]: [Title]
- Maintain each character's unique speech pattern.
- Show don't tell. Sensory detail, subtext, emotion through action.
- Every chapter must advance plot OR deepen character (ideally both).
"""

    if genre_model:
        base += "\n" + genre_model.system_prompt_addon(bible)

    return base


# ── Stage 0: Language Selection ───────────────────────────────────────────────

SUPPORTED_LANGUAGES = {
    "English":    "en",
    "Hindi":      "hi",
    "Spanish":    "es",
    "French":     "fr",
    "Portuguese": "pt",
    "German":     "de",
    "Italian":    "it",
    "Japanese":   "ja",
    "Chinese":    "zh",
    "Arabic":     "ar",
    "Bengali":    "bn",
    "Tamil":      "ta",
    "Telugu":     "te",
    "Marathi":    "mr",
    "Gujarati":   "gu",
}


def select_language(bible: StoryBible, language: str) -> StoryBible:
    """Set story language. Validates against supported list."""
    # Try exact match
    for lang, code in SUPPORTED_LANGUAGES.items():
        if language.lower() == lang.lower() or language.lower() == code.lower():
            bible.language       = lang
            bible.language_code  = code
            bible.stage_complete["language"] = True
            bible.save()
            return bible

    # Partial match
    for lang, code in SUPPORTED_LANGUAGES.items():
        if language.lower() in lang.lower():
            bible.language       = lang
            bible.language_code  = code
            bible.stage_complete["language"] = True
            bible.save()
            return bible

    # Default to English if not found
    bible.language       = "English"
    bible.language_code  = "en"
    bible.stage_complete["language"] = True
    bible.save()
    return bible


# ── Stage 1: Premise Development ──────────────────────────────────────────────

def develop_premise(bible: StoryBible, raw_concept: str, genre_model=None) -> StoryBible:
    """
    Develop premise → logline + theme + genre + tone + arc type.
    Genre model provides arc type suggestions if available.
    """
    client = _client()

    arc_suggestions = []
    if genre_model:
        arc_suggestions = genre_model.recommended_arc_types
    else:
        arc_suggestions = suggest_arc_type("literary")

    arc_desc = "\n".join(f"- {a}: {ARC_DESCRIPTIONS.get(a, '')}" for a in arc_suggestions[:3])

    prompt = f"""Develop this story concept into a full premise.

Story concept: {raw_concept}
Language to write in: {bible.language}

Recommended emotional arc shapes for this genre (pick the best fit):
{arc_desc}

Return ONLY valid JSON:
{{
  "logline": "One sentence: [protagonist] must [goal] or [stakes]. Under 30 words.",
  "theme": "The deeper truth — what this story is ABOUT at its core. One sentence.",
  "genre": "Primary genre (crime/romance/horror/fantasy/literary)",
  "target_audience": "Who this is for (age range, tastes)",
  "tone": "Emotional register (e.g. dark and gritty, light-hearted, epic, intimate, satirical)",
  "emotional_arc_type": "One of: Rags to Riches / Tragedy / Man in Hole / Icarus / Cinderella / Oedipus",
  "premise_summary": "2-3 sentence expanded premise with protagonist, conflict, stakes"
}}"""

    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _extract_json(response.content[0].text)

    bible.premise            = raw_concept
    bible.logline            = data.get("logline", "")
    bible.theme              = data.get("theme", "")
    bible.genre              = data.get("genre", "literary")
    bible.target_audience    = data.get("target_audience", "")
    bible.tone               = data.get("tone", "")
    bible.emotional_arc_type = data.get("emotional_arc_type", "Man in Hole")
    bible.stage_complete["premise"] = True
    bible.save()
    return bible


# ── Stage 2: Title Generation ─────────────────────────────────────────────────

def generate_titles(bible: StoryBible) -> list[str]:
    client = _client()

    prompt = f"""Generate 5 compelling title options for this story.

Logline: {bible.logline}
Theme: {bible.theme}
Genre: {bible.genre}
Tone: {bible.tone}
Language: {bible.language}

Use these 5 approaches (one each):
1. Single evocative word or noun
2. Metaphorical phrase (2-4 words)
3. A question or fragment
4. A character name or place
5. An ironic or unexpected phrase

Titles must be in {bible.language}.

Return ONLY valid JSON: {{"titles": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"]}}"""

    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _extract_json(response.content[0].text)
    titles = data.get("titles", [])
    bible.title_candidates = titles
    bible.stage_complete["title"] = True
    bible.save()
    return titles


def set_title(bible: StoryBible, title: str):
    bible.title = title
    bible.save()


# ── Stage 3: World Building ───────────────────────────────────────────────────

def build_world(bible: StoryBible, genre_model=None) -> WorldBible:
    client = _client()

    world_instructions = genre_model.world_building_prompt() if genre_model else ""

    prompt = f"""Build a detailed world bible for this story.

Story: {bible.logline}
Genre: {bible.genre}
Tone: {bible.tone}
Theme: {bible.theme}
Language: {bible.language}

{world_instructions}

Return ONLY valid JSON with these exact fields (all strings, write in {bible.language}):
{{
  "overview": "2-3 sentence overview of this world",
  "geography": "Key locations, landscape, climate, regions, how people travel",
  "history": "Key past events that shaped the current situation. Timeline of relevant history.",
  "culture": "Customs, values, art, food, clothing, social norms",
  "politics": "Power structures, rulers, factions, ongoing conflicts",
  "economy": "Trade, currency, resources, class system, wealth distribution",
  "religion": "Beliefs, gods/higher powers, rituals, taboos, superstitions",
  "magic_or_tech": "How magic/technology works — rules, costs, limits, who can use it",
  "language": "Notable languages, dialects, naming conventions",
  "unique_elements": "What makes this world distinctive — the 2-3 things that set it apart"
}}

Keep each field to 2-4 sentences maximum. Return complete valid JSON only."""

    data = _call_json(client, MODEL, prompt, max_tokens=6000)
    world = WorldBible.from_dict(data)
    bible.world = world
    bible.stage_complete["world"] = True
    bible.save()
    return world


# ── Stage 4: Character Building ───────────────────────────────────────────────

def build_character(
    bible: StoryBible,
    role: str,
    tier: int = 1,
    subgenre: str = "",
    genre_model=None,
    extra_context: str = "",
) -> CharacterProfile:
    """
    Build a character with tier-appropriate depth.
    Genre model provides archetype-specific prompts.
    """
    client = _client()

    # Get genre-specific prompt if available
    if genre_model:
        genre_prompt = genre_model.character_building_prompt(role, tier, subgenre)
    else:
        genre_prompt = f"Create a {role} character for {bible.genre} fiction (Tier {tier})."

    existing_chars = bible.character_list_for_prompt()

    if tier == 1:
        json_template = """{
  "name": "Character's full name",
  "role": "protagonist/antagonist/mentor/ally/etc.",
  "age": "Age or age range",
  "physical_description": "Specific physical appearance — 3-4 details that matter to the story",
  "speech_pattern": "How they talk: accent, vocabulary, rhythm, distinctive phrases",
  "ghost": "Specific past wound/trauma that shaped them",
  "lie": "The misbelief they carry because of the ghost",
  "want": "External goal driving them through the plot",
  "need": "Internal truth they must learn",
  "flaw": "The weakness that creates conflict",
  "strength": "The capability that makes them effective",
  "arc_type": "positive/negative/flat",
  "arc_summary": "How they transform (or don't) by the end",
  "vogler_archetype": "Hero/Mentor/Shadow/Ally/etc.",
  "enneagram_type": "e.g. Type 8 (Challenger)",
  "mbti_type": "e.g. INTJ",
  "ocean_scores": {"O": 0.7, "C": 0.8, "E": 0.4, "A": 0.4, "N": 0.5},
  "relationships": {},
  "tier": 1,
  "is_pov_character": true
}"""
    elif tier == 2:
        json_template = """{
  "name": "Character's name",
  "role": "their role",
  "age": "age or range",
  "physical_description": "2 key details",
  "speech_pattern": "how they talk",
  "ghost": "their wound (brief)",
  "lie": "their misbelief",
  "want": "their goal",
  "need": "what they must learn",
  "flaw": "their weakness",
  "strength": "their strength",
  "arc_type": "positive/negative/flat",
  "arc_summary": "brief arc",
  "tier": 2,
  "is_pov_character": false
}"""
    else:
        json_template = """{
  "name": "Character's name",
  "role": "their function",
  "age": "rough age",
  "flaw": "one defining trait",
  "strength": "one defining trait",
  "speech_pattern": "one key speech detail",
  "tier": 3,
  "is_pov_character": false
}"""

    prompt = f"""Create a new character for this story.

STORY CONTEXT:
Logline: {bible.logline}
Genre: {bible.genre} | Tone: {bible.tone}
Language: {bible.language}

EXISTING CHARACTERS (avoid duplicating):
{existing_chars}

GENRE CHARACTER GUIDANCE:
{genre_prompt}

{f"Additional context: {extra_context}" if extra_context else ""}

Write character name and all text fields in {bible.language} where appropriate.
Return ONLY valid JSON matching this template:
{json_template}

Keep each string field concise (1-3 sentences). Escape quotes in text properly. Return complete valid JSON only."""

    data = _call_json(client, MODEL, prompt, max_tokens=4000)

    # Ensure tier is set
    data["tier"] = tier

    char = CharacterProfile.from_dict(data)
    bible.add_character(char)
    bible.stage_complete["characters"] = True
    bible.save()
    return char


# ── Stage 5: Beat Generation ──────────────────────────────────────────────────

def generate_beats(bible: StoryBible) -> list[StoryBeat]:
    client = _client()

    beat_names_str = "\n".join(
        f"{num}. {name} ({act})" for num, name, act in BEAT_NAMES
    )

    prompt = f"""Create the 15 Save the Cat story beats for this specific story.

STORY:
Title: {bible.title or "(untitled)"}
Logline: {bible.logline}
Theme: {bible.theme}
Genre: {bible.genre} | Tone: {bible.tone}
Emotional arc: {bible.emotional_arc_type}

CHARACTERS:
{bible.character_list_for_prompt()}

WORLD:
{bible.world.overview}

THE 15 BEATS (fill in what actually happens in THIS story):
{beat_names_str}

Return ONLY valid JSON:
{{
  "beats": [
    {{
      "number": 1,
      "name": "Opening Image",
      "act": "Act I",
      "description": "Exactly what happens in this story for this beat (2-3 specific sentences)",
      "chapter_hint": "Likely chapter number(s)"
    }}
  ]
}}

All 15 beats must be specific to this story — not generic descriptions.
Keep each description to 2-3 sentences. Return complete valid JSON only."""

    data = _call_json(client, MODEL, prompt, max_tokens=8000)
    beats = [StoryBeat(**b) for b in data["beats"]]
    bible.beats = beats
    bible.stage_complete["beats"] = True
    bible.save()
    return beats


# ── Stage 6: Chapter Planning ─────────────────────────────────────────────────

def plan_chapters(
    bible: StoryBible,
    total_chapters: int,
    genre_model=None,
) -> list[ChapterPlan]:
    """
    Create chapter-by-chapter outline with emotional intensity targets.
    Uses Reagan arc + STC beats to assign target emotions per chapter.
    """
    client = _client()

    # Pre-compute intensity targets from arc calculator
    intensities = assign_chapter_intensities(
        chapter_count=total_chapters,
        arc_type=bible.emotional_arc_type,
    )

    prompt = f"""Create a {total_chapters}-chapter outline for this story.

STORY:
Title: {bible.title}
Logline: {bible.logline}
Theme: {bible.theme}
Genre: {bible.genre} | Tone: {bible.tone}
Emotional arc: {bible.emotional_arc_type}

BEATS:
{bible.beats_for_prompt()}

CHARACTERS:
{bible.character_list_for_prompt()}

TARGET INTENSITIES PER CHAPTER (0.0-1.0, from arc model):
{chr(10).join(f"Chapter {i+1}: {v:.2f}" for i, v in enumerate(intensities))}

Map all 15 beats across {total_chapters} chapters.

Return ONLY valid JSON:
{{
  "chapters": [
    {{
      "number": 1,
      "title": "Evocative chapter title",
      "beats_covered": [1, 2],
      "pov_character": "POV character name",
      "location": "Where this takes place",
      "summary": "Specific 2-3 sentence summary of what happens",
      "emotional_goal": "What the reader should feel at chapter end",
      "arc_type": "{bible.emotional_arc_type}",
      "target_emotion_intensity": 0.45
    }}
  ]
}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=5000,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _extract_json(response.content[0].text)

    chapter_plans = []
    for i, cp_data in enumerate(data.get("chapters", [])):
        # Inject pre-computed intensity if not provided
        if "target_emotion_intensity" not in cp_data and i < len(intensities):
            cp_data["target_emotion_intensity"] = intensities[i]

        # Add position_pct
        n = cp_data.get("number", i + 1)
        cp_data["position_pct"] = (n - 0.5) / total_chapters

        # Add genre-specific target emotions
        if genre_model:
            cp_data["target_emotions"] = genre_model.suggest_chapter_emotions(
                cp_data["position_pct"], bible.emotional_arc_type
            )

        chapter_plans.append(ChapterPlan.from_dict(cp_data))

    bible.chapter_plan = chapter_plans
    bible.stage_complete["chapter_plan"] = True
    bible.save()
    return chapter_plans


# ── Stage 6b: Scene Drafts ────────────────────────────────────────────────────

def draft_chapter_scenes(
    bible: StoryBible,
    chapter_number: int,
    scene_count: int = 3,
    genre_model=None,
) -> list[SceneDraft]:
    """
    Generate brief scene outlines for a chapter BEFORE full writing.
    Computes Scene Interest Score per scene to determine word count.
    User approves scene drafts before full prose is written.
    """
    client = _client()

    cp = bible.get_chapter_plan(chapter_number)
    if not cp:
        raise ValueError(f"No chapter plan found for chapter {chapter_number}")

    beats_text = "\n".join(
        f"- {next((b.name for b in bible.beats if b.number == n), f'Beat {n}')}"
        for n in cp.beats_covered
    )
    position_pct = cp.position_pct

    prompt = f"""Create {scene_count} brief scene outlines for Chapter {chapter_number}.

CHAPTER INFO:
Title: {cp.title}
Summary: {cp.summary}
Emotional goal: {cp.emotional_goal}
Beats: {beats_text}
POV: {cp.pov_character} | Location: {cp.location}
Story position: {position_pct:.0%} through the story

For each scene, provide:
- A 2-3 sentence description of what happens
- The emotional goal of just this scene
- Which STC beat(s) it covers

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "beats_covered": ["Catalyst"],
      "pov_character": "{cp.pov_character}",
      "location": "Specific location within the chapter setting",
      "brief_description": "2-3 sentences: what happens in this scene",
      "emotional_goal": "What this specific scene should make the reader feel"
    }}
  ]
}}"""

    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _extract_json(response.content[0].text)

    scene_drafts = []
    previous_scores: list[SceneInterestScore] = []

    for sd_data in data.get("scenes", []):
        # Score with Scene Interest Score
        target_emotions = {}
        if genre_model:
            target_emotions = genre_model.suggest_chapter_emotions(
                position_pct, bible.emotional_arc_type
            )

        sis = score_scene(
            scene_draft=sd_data.get("brief_description", ""),
            beats_covered=sd_data.get("beats_covered", []),
            position_pct=position_pct,
            previous_scores=previous_scores,
            target_emotions=target_emotions,
        )
        previous_scores.append(sis)

        scene_draft = SceneDraft(
            scene_number=sd_data.get("scene_number", len(scene_drafts) + 1),
            beats_covered=sd_data.get("beats_covered", []),
            pov_character=sd_data.get("pov_character", cp.pov_character),
            location=sd_data.get("location", cp.location),
            brief_description=sd_data.get("brief_description", ""),
            emotional_goal=sd_data.get("emotional_goal", ""),
            target_emotions=target_emotions,
            sis_estimate=sis.sis_total,
            word_count_target=sis.word_count_target,
            narrative_mode=sis.narrative_mode,
        )
        scene_drafts.append(scene_draft)

    # Store in chapter plan
    cp.scenes = [sd.to_dict() for sd in scene_drafts]
    cp.scene_interest_scores = [sd.sis_estimate for sd in scene_drafts]
    bible.save()

    return scene_drafts


# ── Stage 7: Write Chapter ────────────────────────────────────────────────────

def write_chapter(
    bible: StoryBible,
    chapter_number: int,
    genre_model=None,
    scene_scores: list = None,
    extra_instructions: str = "",
    regeneration_focus: str = "",
    use_thinking: bool = False,
    save_to_bible: bool = True,
) -> str:
    """
    Write a chapter using full story bible + genre-specific instructions.
    If use_thinking=True, enables extended thinking for pivotal chapters.
    When save_to_bible=False (quality-gate retries), the draft is ephemeral.
    """
    client = _client()
    cp = bible.get_chapter_plan(chapter_number)

    # Genre-specific writing instructions
    genre_instructions = ""
    if genre_model and cp:
        genre_instructions = genre_model.chapter_writing_instructions(
            bible, cp, scene_scores or []
        )

    if cp:
        beats_text = "\n".join(
            f"- Beat {n}: {next((b.name + ': ' + b.description for b in bible.beats if b.number == n), f'Beat {n}')}"
            for n in cp.beats_covered
        )

        # Scene drafts if approved
        scene_draft_text = ""
        if cp.scenes:
            scene_draft_text = "\n\nSCENE-BY-SCENE PLAN:\n" + "\n".join(
                f"Scene {sd.get('scene_number', i+1)}: {sd.get('brief_description', '')}"
                f" (target: {sd.get('word_count_target', 1500)} words, mode: {sd.get('narrative_mode', 'Scene')})"
                for i, sd in enumerate(cp.scenes)
            )

        instruction = f"""Write Chapter {chapter_number}: "{cp.title}"

POV Character: {cp.pov_character}
Location: {cp.location}
Story beats to cover:
{beats_text}

What must happen: {cp.summary}
Reader should feel: {cp.emotional_goal}
Emotional intensity target: {cp.target_emotion_intensity:.0%}
{scene_draft_text}
{genre_instructions}
{f"Regeneration guidance (previous attempt failed — fix these specifically): {regeneration_focus}" if regeneration_focus else ""}
{f"Additional guidance: {extra_instructions}" if extra_instructions else ""}

Begin directly with: # Chapter {chapter_number}: {cp.title}
Write the full chapter in literary prose. Do not summarize — write the actual scenes.
Target word count: {cp.word_count_target:,} words."""
    else:
        instruction = f"Write Chapter {chapter_number}.\n{extra_instructions or ''}"

    if save_to_bible:
        bible.add_message("user", instruction)
        api_messages = _messages_for_api(bible)
    else:
        api_messages = _messages_for_api(bible, extra_user=instruction)

    create_kwargs = dict(
        model=MODEL,
        max_tokens=12000,
        system=_system_prompt(bible, genre_model),
        messages=api_messages,
    )
    if use_thinking:
        create_kwargs["max_tokens"] = 18000
        create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": THINK_BUDGET}

    response = client.messages.create(**create_kwargs)

    if use_thinking:
        chapter_text = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
    else:
        chapter_text = response.content[0].text

    title = cp.title if cp else f"Chapter {chapter_number}"
    if save_to_bible:
        bible.add_message("assistant", chapter_text)
        bible.add_chapter(chapter_number, title, chapter_text)
        bible.save()
    return chapter_text


def write_chapter_gated(
    bible: StoryBible,
    chapter_number: int,
    genre_model=None,
    scene_scores: list = None,
    extra_instructions: str = "",
) -> tuple[str, "QualityReport"]:
    """
    Write a chapter with automatic quality gating.
    Retries up to 3 times if quality score is below genre threshold.
    Returns (chapter_text, quality_report).
    """
    from core.quality_gate import gate_chapter

    cp = bible.get_chapter_plan(chapter_number)
    total_chapters = len(bible.chapter_plan) or 10

    def _write(regeneration_focus: str = "") -> str:
        return write_chapter(
            bible, chapter_number,
            genre_model=genre_model,
            scene_scores=scene_scores,
            extra_instructions=extra_instructions,
            regeneration_focus=regeneration_focus,
            save_to_bible=False,
        )

    initial_text = _write()

    final_text, report = gate_chapter(
        chapter_text=initial_text,
        chapter_number=chapter_number,
        total_chapters=total_chapters,
        genre=genre_model.genre if genre_model else bible.genre,
        write_fn=_write,
        emotional_goal=cp.emotional_goal if cp else "",
        target_emotions=cp.target_emotions if cp else {},
        scene_scores=scene_scores or [],
        character_summaries=bible.character_compact_list(),
        genre_model=genre_model,
        bible=bible,
        chapter_plan=cp,
        emotional_arc_type=bible.emotional_arc_type,
    )

    title = cp.title if cp else f"Chapter {chapter_number}"
    _persist_approved_chapter(bible, chapter_number, final_text, title)

    return final_text, report


# ── Stage 8: Refine Chapter ───────────────────────────────────────────────────

def refine_chapter(bible: StoryBible, chapter_number: int, feedback: str) -> str:
    client = _client()

    instruction = (
        f"Revise Chapter {chapter_number} based on this feedback:\n\n{feedback}\n\n"
        f"Rewrite the full chapter incorporating all changes. Start with the chapter header."
    )
    bible.add_message("user", instruction)

    response = client.messages.create(
        model=MODEL,
        max_tokens=12000,
        system=_system_prompt(bible),
        messages=_messages_for_api(bible),
    )

    revised = response.content[0].text
    bible.add_message("assistant", revised)

    cp = bible.get_chapter_plan(chapter_number)
    title = cp.title if cp else f"Chapter {chapter_number}"
    bible.add_chapter(chapter_number, title, revised)
    bible.save()
    return revised


# ── Stage 9: Ask Question ─────────────────────────────────────────────────────

def ask_question(bible: StoryBible, question: str, genre_model=None) -> str:
    client = _client()
    bible.add_message("user", question)

    response = client.messages.create(
        model=MODEL_FAST,
        max_tokens=2000,
        system=_system_prompt(bible, genre_model),
        messages=_messages_for_api(bible),
    )

    answer = response.content[0].text
    bible.add_message("assistant", answer)
    bible.save()
    return answer
