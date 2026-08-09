"""
genres/fantasy/psychology.py — Fantasy reader psychology.

Research:
- Bettelheim (1976): fairy tale psychology — significance, destiny, guidance
- Jung: individuation journey, archetypes
- Campbell (1949): monomyth
- Tolkien: eucatastrophe — sudden joyous turn
"""

READER_CORE_NEEDS = [
    "significance",      # hidden potential waiting to be revealed
    "meaning_seeking",   # hidden destiny in ordinary life
    "guidance_need",     # wise mentor in chaotic world
    "agency",            # ability to make difference
    "belonging",         # found family, community acceptance
    "escapism",          # healthy retreat from reality
]

CHOSEN_ONE_PSYCHOLOGY = {
    "core_appeal": "Wish fulfillment — being uniquely important, recognition of hidden potential",
    "why_works":   "Ancient pattern (Christ narrative, mythology) — pre-literary resonance",
    "needs_served": ["significance", "destiny", "belonging", "purpose"],
    "reader_identification": "outsider status — readers who feel unrecognized",
}

MENTOR_PSYCHOLOGY = {
    "departure_reason": "Protagonist must integrate lessons and stand alone — growth requires independence",
    "departure_function": "Grief + forced self-reliance = transformation",
    "flaws_required": True,
    "departure_timing": "After core lesson internalized but before climax",
}

WORLDBUILDING_RULES = {
    "front_loading_danger": "Information before emotional investment = reader abandonment",
    "reveal_mechanism": "Through dialogue, conflict, character observation",
    "include_only": "Information critical to character's present moment",
    "magic_reveal_pacing": "Gradual — one new element per chapter maximum",
    "show_consequences_of_magic": True,
}

SENSE_OF_WONDER_TRIGGERS = [
    "first_glimpse_of_magic",
    "scale_reveal_of_world",
    "unexpected_rule_of_magic_system",
    "mythic_resonance_moment",
    "found_family_scene",
    "eucatastrophe_moment",
]

SATISFACTION_TRIGGERS = {
    "eucatastrophe":           1.0,
    "hero_earns_destiny":      0.90,
    "mentor_sacrifice":        0.85,
    "world_detail_pays_off":   0.75,
    "found_family_bond":       0.80,
}

DISSATISFACTION_TRIGGERS = {
    "world_info_dump_before_caring":  True,
    "magic_without_cost":            True,
    "mentor_omniscient":             True,
    "chosen_one_unearned":           True,
    "sacrifice_without_weight":      True,
}

SUSPENSE_WEIGHTS = {
    "imminence":       0.30,
    "importance":      0.35,
    "foregroundedness": 0.25,
    "confidence":      0.10,
}
