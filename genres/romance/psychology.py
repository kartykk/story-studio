"""
genres/romance/psychology.py — Romance reader psychology.

Research:
- Bowlby (1969): Attachment theory — romance satisfies fundamental need to be chosen
- Mar et al. (2006): Embodied cognition — brain simulates touch/intimacy during reading
- Kidd & Castano (2013): Theory of Mind — parasocial bonds with characters
- Chapman (1992): 5 Love Languages
"""

READER_CORE_NEEDS = [
    "attachment_fulfillment",       # being chosen, seen, loved — Bowlby
    "safe_emotional_exploration",   # vulnerability without real risk
    "embodied_cognition",           # brain simulates touch/kiss (proven)
    "parasocial_bond",              # deep connection to characters
    "wish_fulfillment",             # ideal relationship modeled
]

SATISFACTION_TRIGGERS = {
    "black_moment_devastating":      1.0,    # must feel genuinely hopeless
    "hea_earned":                    0.95,   # HEA must follow real transformation
    "vulnerability_reciprocated":    0.85,
    "character_transformation":      0.80,
    "the_grovel":                    0.85,   # hero's sincere apology
    "emotional_communication":       0.75,
}

DISSATISFACTION_TRIGGERS = {
    "no_hea":                        True,
    "black_moment_too_mild":         True,   # reader not devastated = unsatisfying
    "more_than_2_separations":       True,   # frustration threshold
    "hero_never_apologizes":         True,   # "the grovel" is expected
    "sudden_personality_change":     True,   # transformation must be earned
    "forced_misunderstanding":       True,   # communication failure that's not believable
}

SUSPENSE_WEIGHTS = {
    "imminence":       0.25,
    "importance":      0.35,     # emotional stakes paramount
    "foregroundedness": 0.25,
    "confidence":      0.15,
}

BLACK_MOMENT_RULES = {
    "must_feel_permanent":           True,
    "cause_from_character_flaw":     True,   # not external plot mechanics
    "both_characters_contribute":    True,   # not one person's fault entirely
    "reader_should_not_see_solution": True,
    "minimum_emotional_devastation":  0.80,  # SIS/emotion score
}

HEA_RULES = {
    "both_characters_transformed":    True,
    "external_obstacle_resolved":     True,
    "internal_lie_defeated":          True,
    "explicit_commitment":            True,  # verbal or clear action of commitment
    "reader_believes_it_will_last":   True,
}

PACING_RULES = {
    "scene_sequel_ratio":   0.55,
    "tension_relief_cycle": True,      # every high tension scene followed by relief
    "intimacy_escalation":  "gradual", # physical/emotional intimacy must build slowly
    "dialogue_ratio":       "high",    # romance = character-driven = more dialogue
}
