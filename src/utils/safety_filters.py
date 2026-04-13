"""
Hard-coded safety layer — runs BEFORE the LLM.
Emergency keywords detected here bypass LLM confidence scoring entirely.
"""

# Symptom phrases that ALWAYS trigger EMERGENCY routing regardless of LLM output
EMERGENCY_KEYWORDS: list[tuple[str, str]] = [
    # (keyword_pattern, red_flag_label)
    ("chest pain", "Chest pain"),
    ("chest pressure", "Chest pressure"),
    ("chest tightness", "Chest tightness"),
    ("heart attack", "Chest pain / cardiac concern"),
    ("can't breathe", "Severe breathing difficulty"),
    ("cannot breathe", "Severe breathing difficulty"),
    ("difficulty breathing", "Breathing difficulty"),
    ("shortness of breath", "Shortness of breath"),
    ("not breathing", "Breathing stopped"),
    ("stopped breathing", "Breathing stopped"),
    ("stroke", "Stroke signs"),
    ("face drooping", "Stroke sign — face drooping"),
    ("arm weakness", "Stroke sign — arm weakness"),
    ("slurred speech", "Stroke sign — slurred speech"),
    ("can't speak", "Stroke sign — speech difficulty"),
    ("cannot speak", "Stroke sign — speech difficulty"),
    ("seizure", "Seizure"),
    ("convulsion", "Convulsion"),
    ("unconscious", "Loss of consciousness"),
    ("passed out", "Loss of consciousness"),
    ("fainted", "Loss of consciousness"),
    ("severe bleeding", "Severe bleeding"),
    ("bleeding heavily", "Heavy bleeding"),
    ("not stopping bleeding", "Uncontrolled bleeding"),
    ("overdose", "Suspected overdose"),
    ("poisoning", "Suspected poisoning"),
    ("anaphylaxis", "Anaphylaxis"),
    ("allergic reaction", "Severe allergic reaction"),
    ("throat closing", "Anaphylaxis — throat closing"),
    ("can't swallow", "Severe swallowing difficulty"),
    ("severe trauma", "Severe trauma"),
    ("hit by", "Trauma"),
    ("head injury", "Head injury"),
    ("broken bone", "Fracture / severe trauma"),
    ("heart racing", "Severe palpitations"),
    ("heart pounding", "Severe palpitations"),
]

# Phrases that indicate the user is trying to get a diagnosis (block & redirect)
DIAGNOSIS_REQUEST_PATTERNS: list[str] = [
    "do i have",
    "is this",
    "what disease",
    "what condition",
    "what illness",
    "diagnose me",
    "tell me what i have",
    "what is wrong with me",
]


def is_gibberish(text: str) -> bool:
    """
    Detect if a patient message is meaningless / gibberish.
    Returns True when the input clearly cannot contain symptom information.
    """
    text = text.strip()
    if not text or len(text) < 2:
        return True

    # Count alphabetic characters
    alpha = sum(1 for c in text if c.isalpha())
    total = len(text)

    # Mostly non-alphabetic (symbols, numbers only) and short → gibberish
    if total < 4 and alpha == 0:
        return True

    # Check every word: a word of 4+ letters with no vowels is gibberish
    VOWELS = set("aeiouAEIOU")
    words = text.split()
    gibberish_words = 0
    for word in words:
        alpha_in_word = [c for c in word if c.isalpha()]
        if len(alpha_in_word) >= 4 and not any(c in VOWELS for c in alpha_in_word):
            gibberish_words += 1

    # If more than half the words look like gibberish, reject
    if words and gibberish_words / len(words) > 0.5:
        return True

    # Very short with no vowels at all
    if alpha >= 2 and not any(c in VOWELS for c in text):
        return True

    return False


def detect_red_flags(text: str) -> list[str]:
    """
    Scan patient message for hard-coded emergency keywords.
    Returns list of red flag labels found.
    """
    text_lower = text.lower()
    found = []
    for keyword, label in EMERGENCY_KEYWORDS:
        if keyword in text_lower and label not in found:
            found.append(label)
    return found


def is_diagnosis_request(text: str) -> bool:
    """Detect if the user is asking for a diagnosis."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in DIAGNOSIS_REQUEST_PATTERNS)


def sanitize_llm_response(text: str) -> str:
    """
    Post-process LLM output to strip any accidentally generated diagnosis language.
    Replaces diagnosis phrases with safe alternatives.
    """
    diagnosis_replacements = [
        ("you have ", "symptoms suggest "),
        ("you've got ", "symptoms suggest "),
        ("you are suffering from ", "symptoms may indicate the need for evaluation for "),
        ("diagnosed with ", "showing symptoms that require evaluation for "),
        ("it is ", "this may be "),
        ("this is ", "this may be "),
    ]
    result = text
    for bad, good in diagnosis_replacements:
        result = result.replace(bad, good)
    return result
