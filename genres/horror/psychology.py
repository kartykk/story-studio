"""
genres/horror/psychology.py — Horror reader psychology.

Research:
- Zillmann & Tamborini (1996): Excitation Transfer Theory
- Terror Management Theory (Greenberg et al.): mortality confrontation
- Three-stage fear model: dread → terror → horror
"""

ENJOYMENT_MECHANISM = {
    "type": "excitation_transfer",
    "principle": "Fear converts to euphoria when threat resolves. Enjoyment proportional to buildup intensity.",
    "safety_awareness_required": True,
    "sensation_seeking_correlation": "strong",
}

READER_CORE_NEEDS = [
    "controlled_fear_exposure",
    "mortality_confrontation",
    "bodily_integrity_violation",
    "pattern_recognition_reward",
    "catharsis",
]

FEAR_STAGES = {
    "dread": {
        "definition": "Anticipation of unknown threat — imagination fills blanks",
        "duration_pct": (0.50, 0.70),
        "mechanism": "Withhold information — reader's imagination exceeds any description",
        "reader_state": "Waiting, unease",
    },
    "terror": {
        "definition": "Known threat revealed",
        "duration": "brief burst",
        "mechanism": "After long dread, revelation hits harder",
        "reader_state": "Adrenaline peak, fight-or-flight",
    },
    "horror": {
        "definition": "Post-threat processing — emotional aftermath",
        "mechanism": "Allow processing time before next cycle",
        "reader_state": "Catharsis, reflection, integration",
    },
}

SATISFACTION_TRIGGERS = {
    "sustained_dread_paid_off":   1.0,
    "threat_understood_too_late": 0.85,
    "final_girl_empowered":       0.80,
    "false_safety_broken":        0.90,
    "sacrifice_meaningful":       0.75,
}

DISSATISFACTION_TRIGGERS = {
    "monster_shown_too_early":       True,
    "victims_not_developed":         True,
    "false_scare_overuse":           True,   # >7 = numbness
    "psychological_horror_explained": True,
    "cosmic_horror_resolved":         True,
    "threat_not_understandable":      True,
}

SUSPENSE_WEIGHTS = {
    "imminence":       0.40,
    "importance":      0.25,
    "foregroundedness": 0.25,
    "confidence":      0.10,
}

ATMOSPHERE_RULES = {
    "sensory_detail":       "prioritize sound and smell over sight for horror",
    "setting_hostile":      True,
    "false_safety":         "establish safety then violate it",
    "isolation_principle":  "cut off help before threat arrives",
    "ordinary_made_wrong":  "familiar things slightly off = uncanny valley effect",
}
