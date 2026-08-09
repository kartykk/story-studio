"""
genres/literary/psychology.py — Literary fiction reader psychology.

Research:
- Kidd & Castano (2013): literary fiction improves Theory of Mind scores
- Mar et al. (2006): narrative transportation; simulation hypothesis
- Aristotle: catharsis — emotional purging through art
- James (1884): The Art of Fiction — "render reality"
"""

READER_CORE_NEEDS = [
    "theory_of_mind_exercise",    # understanding others' inner states (Kidd & Castano)
    "emotional_authenticity",     # internal states feel recognized/real
    "meaning_making",             # finding significance in experience
    "aesthetic_pleasure",         # language beauty as intrinsic reward
    "perspective_expansion",      # seeing through fundamentally different eyes
]

THEORY_OF_MIND_TRIGGERS = [
    "deep_interior_monologue",
    "unreliable_perception_revealed",
    "character_contradicts_themselves_believably",
    "subtext_scene_two_things_said_three_meant",
    "epiphany_earned_through_accumulated_detail",
]

SATISFACTION_TRIGGERS = {
    "recognition":           1.0,     # 'I've felt this too' — highest literary satisfaction
    "psychological_truth":   0.95,
    "earned_epiphany":       0.90,
    "language_beauty":       0.85,
    "authentic_ambiguity":   0.75,
}

DISSATISFACTION_TRIGGERS = {
    "false_resolution":             True,
    "character_inconsistency":      True,
    "ambiguity_without_meaning":    True,
    "sentimentality_over_truth":    True,
    "explaining_the_subtext":       True,
    "plot_over_character":          True,
}

EPIPHANY_RULES = {
    "must_be_earned":              True,
    "through_accumulated_detail":  True,
    "not_stated_directly":         True,
    "reader_arrives_with_character": True,
    "position_pct":                (0.70, 0.90),
}

UNRELIABLE_NARRATOR_RULES = {
    "reader_must_detect":          True,
    "contradictions_findable":     True,
    "reveal_mechanism":            "accumulation_of_contradictions",
    "no_outright_deception":       True,
}

SUBTEXT_PRINCIPLE = {
    "definition": "Character says one thing; means another; reveals a third",
    "mechanism": "What is NOT said carries as much weight as what is said",
    "how_to_write": "Action, object, or environment expresses what character cannot say",
    "hemingway": "90% below the surface — the reader fills it in",
}

SUSPENSE_WEIGHTS = {
    "imminence":       0.20,
    "importance":      0.35,     # emotional stakes over external danger
    "foregroundedness": 0.30,
    "confidence":      0.15,
}
