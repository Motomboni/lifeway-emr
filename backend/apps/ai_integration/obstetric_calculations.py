"""
Obstetric calculation helpers for the Clinical AI Scribe.

Naegele's rule for EDD; EGA from LMP relative to reference date.
"""

import re
from datetime import date, datetime, timedelta
from typing import Optional

# Keywords suggesting antenatal/maternity context
OBSTETRIC_KEYWORDS = re.compile(
    r"\b("
    r"pregnant|pregnancy|antenatal|\banc\b|maternity|maternal|"
    r"\blmp\b|last menstrual|edd|gestational|gravida|\bpara\b|"
    r"fetal|foetal|trimester|obstetric|booking visit|"
    r"symphysio|sfh|fhr|fetal heart|cephalic|breech|"
    r"morning sickness|preeclampsia|eclampsia|iptp|folic acid|"
    r"iron tablet|tt injection|tetanus toxoid"
    r")\b",
    re.IGNORECASE,
)

LMP_PATTERNS = [
    # LMP 12/03/2026 or 12-03-2026
    re.compile(
        r"\blmp\b[^0-9]{0,20}(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"last menstrual period[^0-9]{0,20}(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})",
        re.IGNORECASE,
    ),
    # LMP: 12 March 2026
    re.compile(
        r"\blmp\b[^a-zA-Z]{0,10}(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
        r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{4})",
        re.IGNORECASE,
    ),
]

MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def calculate_edd(lmp: date) -> date:
    """EDD = LMP + 280 days (40 weeks), equivalent to Naegele's rule."""
    return lmp + timedelta(days=280)


def calculate_ega(lmp: date, reference: date) -> tuple[int, int]:
    """Return (weeks, days) gestational age from LMP to reference date."""
    if reference < lmp:
        return 0, 0
    delta_days = (reference - lmp).days
    weeks, days = divmod(delta_days, 7)
    return weeks, days


def _parse_dmy(day: int, month: int, year: int) -> Optional[date]:
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def extract_lmp_from_text(text: str) -> Optional[date]:
    """Best-effort LMP extraction from transcript text."""
    if not text:
        return None

    for pattern in LMP_PATTERNS[:2]:
        match = pattern.search(text)
        if match:
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
            parsed = _parse_dmy(d, m, y)
            if parsed:
                return parsed

    match = LMP_PATTERNS[2].search(text)
    if match:
        day = int(match.group(1))
        month_key = match.group(2).lower()
        year = int(match.group(3))
        month = MONTH_MAP.get(month_key)
        if month:
            return _parse_dmy(day, month, year)

    return None


def is_obstetric_context(text: str, force_antenatal: bool = False) -> bool:
    if force_antenatal:
        return True
    if not text:
        return False
    return bool(OBSTETRIC_KEYWORDS.search(text))


def build_obstetric_context_block(
    transcript: str, reference: Optional[date] = None
) -> str:
    """
    Pre-compute EDD/EGA from extracted LMP for injection into the AI user prompt.
    Returns empty string if no LMP found.
    """
    ref = reference or date.today()
    lmp = extract_lmp_from_text(transcript)
    if not lmp:
        return ""

    edd = calculate_edd(lmp)
    weeks, days = calculate_ega(lmp, ref)

    return (
        f"\n\n--- PRE-CALCULATED OBSTETRIC DATA (use these values; reference date {ref.isoformat()}) ---\n"
        f"LMP: {lmp.strftime('%d %B %Y')}\n"
        f"EDD (Naegele's rule): {edd.strftime('%d %B %Y')}\n"
        f"EGA: {weeks} weeks {days} days\n"
        f"--- END PRE-CALCULATED DATA ---"
    )


def resolve_template(note_type: str, transcript: str) -> str:
    """
    Resolve note template: 'antenatal', 'soap', 'summary', or 'discharge'.
    note_type 'auto' detects from transcript.
    """
    normalized = (note_type or "auto").strip().lower()
    if normalized in ("antenatal", "anc", "maternity", "obstetric"):
        return "antenatal"
    if normalized == "soap":
        return "soap"
    if normalized == "summary":
        return "summary"
    if normalized == "discharge":
        return "discharge"
    if normalized == "auto":
        return "antenatal" if is_obstetric_context(transcript) else "soap"
    return "soap"
