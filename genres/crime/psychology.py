"""
genres/crime/psychology.py — Crime reader psychology rules.

Research sources:
- Brewer & Lichtenstein (1982): suspense formula r=0.8234
- Agatha Christie autopsy studies: red herring psychology
- Nielsen reader motivation surveys: crime readers' core needs
- Cognitive science of detective fiction (Zunshine 2006)
"""

READER_CORE_NEEDS = [
    "desire_for_order",         # crime disrupts order; story restores it
    "morbid_curiosity",         # biological drive for pattern recognition
    "safe_fear_exploration",    # vicariously experiencing danger
    "moral_testing_ground",     # testing ideas of guilt, justice, right/wrong
    "mental_stimulation",       # puzzle-solving satisfaction
]

SATISFACTION_TRIGGERS = {
    "justice_restored":          1.0,    # highest — reader came for this
    "culprit_unmasked":          0.9,
    "detective_insight_moment":  0.85,
    "character_reveals_motive":  0.80,
    "clever_red_herring":        0.70,   # fair clue that fooled reader = delight
    "cliffhanger_resolved":      0.65,
}

DISSATISFACTION_TRIGGERS = {
    "culprit_introduced_too_late":      True,  # must appear before 50% mark
    "red_herring_without_fair_clue":    True,  # clue must exist in hindsight
    "coincidence_solves_crime":         True,  # must be deduction, not luck
    "justice_not_served":               True,  # (except Noir — expected)
    "too_many_suspects_introduced_late": True,
}

# Suspense formula (Brewer & Lichtenstein) — crime-tuned weights
SUSPENSE_FORMULA = {
    "description": "Suspense = (Imminence × Importance × Foregroundedness) / (1 + Confidence)",
    "r_value": 0.8234,
    "weights": {
        "imminence":       0.35,
        "importance":      0.30,
        "foregroundedness": 0.25,
        "confidence":      0.10,
    },
}

RED_HERRING_RULES = {
    "spring_from_character_psychology":    True,  # not arbitrary mechanics
    "last_minute_most_effective":          True,  # one final diversion before reveal
    "reveal_incriminating_before_clearing": True,
    "never_introduce_culprit_last_chapter": True,
    "must_have_fair_clue_in_text":         True,  # reader can solve it in hindsight
}

CULPRIT_RULES = {
    "introduce_by_pct":       0.50,    # culprit must appear by 50%
    "motive_understandable":  True,    # even if not sympathetic
    "not_most_obvious_suspect": True,  # at least one strong red herring
    "clues_planted_early":    True,
}

INVESTIGATION_BEAT_STRUCTURE = {
    "beat_count": (5, 7),
    "each_beat_must": [
        "reveal new information",
        "either confirm or rule out a suspect",
        "raise stakes or add complication",
    ],
    "pressure_valve_frequency": 3,   # every 3 investigation beats, add a personal scene
}

PACING_RULES = {
    "scene_sequel_ratio":      0.70,   # 70% scene (action), 30% sequel (reflection)
    "max_consecutive_high":    2,      # anti-monotony
    "cliffhanger_rate":        0.80,
    "chapter_ending_types": [
        "revelation_cliffhanger",   # new info that changes everything
        "danger_cliffhanger",       # protagonist in immediate peril
        "question_cliffhanger",     # new question raised, not answered
        "time_pressure_cliffhanger", # deadline introduced or accelerated
    ],
}
