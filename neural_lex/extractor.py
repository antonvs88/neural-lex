from __future__ import annotations

import re

from .finlex import find_section_references, split_into_sections
from .models import ConditionLiteral, LogicAtom, Section

MUST_NOT_RE = re.compile(r"\b(ei\s+saa|on\s+kielletty)\b", flags=re.IGNORECASE)
MUST_RE = re.compile(
    r"\b(tulee|pitää|on\s+\S*tt[äa]v[äa]|on\s+noudatettava)\b",
    flags=re.IGNORECASE,
)
MAY_RE = re.compile(r"\b(saa|voi)\b", flags=re.IGNORECASE)

ACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bväist", flags=re.IGNORECASE), "yield"),
    (re.compile(r"\bpysäh", flags=re.IGNORECASE), "stop"),
    (re.compile(r"\bohit", flags=re.IGNORECASE), "overtake"),
    (re.compile(r"\bkäänt", flags=re.IGNORECASE), "turn"),
    (re.compile(r"\bajaa|\bjatkaa|\bliikku", flags=re.IGNORECASE), "proceed"),
]

TRIGGER_PATTERNS: list[tuple[re.Pattern[str], ConditionLiteral]] = [
    (
        re.compile(r"\bristey", flags=re.IGNORECASE),
        ConditionLiteral("approaching_intersection", True),
    ),
    (
        re.compile(r"\boikealta", flags=re.IGNORECASE),
        ConditionLiteral("coming_from_right", True),
    ),
    (
        re.compile(r"\bväistämismerkki|\bkärkikolmio|\bstop-merkki", flags=re.IGNORECASE),
        ConditionLiteral("has_yield_sign", True),
    ),
    (
        re.compile(r"\bliikennevalo", flags=re.IGNORECASE),
        ConditionLiteral("traffic_lights_present", True),
    ),
    (
        re.compile(r"\bsuojatie", flags=re.IGNORECASE),
        ConditionLiteral("at_crosswalk", True),
    ),
    (
        re.compile(r"\bpolkupyör|\bpyörätie", flags=re.IGNORECASE),
        ConditionLiteral("is_bicycle", True),
    ),
    (
        re.compile(r"\braitiovaunu", flags=re.IGNORECASE),
        ConditionLiteral("tram_present", True),
    ),
    (
        re.compile(r"\bilman\s+väistämismerk", flags=re.IGNORECASE),
        ConditionLiteral("has_yield_sign", False),
    ),
    (
        re.compile(r"\bei\s+ole\s+väistämismerk", flags=re.IGNORECASE),
        ConditionLiteral("has_yield_sign", False),
    ),
    (
        re.compile(r"\bei\s+ole\s+liikennevalo", flags=re.IGNORECASE),
        ConditionLiteral("traffic_lights_present", False),
    ),
]

SUBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bkuljettaj", flags=re.IGNORECASE), "driver"),
    (re.compile(r"\bpolkupyöräilij", flags=re.IGNORECASE), "cyclist"),
    (re.compile(r"\bjalankulkij", flags=re.IGNORECASE), "pedestrian"),
    (re.compile(r"\braitiovaunun\s+kuljettaj", flags=re.IGNORECASE), "tram_driver"),
]

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def detect_modality(sentence: str) -> str | None:
    if MUST_NOT_RE.search(sentence):
        return "must_not"
    if MUST_RE.search(sentence):
        return "must"
    if MAY_RE.search(sentence):
        return "may"
    return None


def detect_action(sentence: str) -> str:
    for pattern, action in ACTION_PATTERNS:
        if pattern.search(sentence):
            return action
    return "comply"


def detect_subject(sentence: str) -> str:
    for pattern, subject in SUBJECT_PATTERNS:
        if pattern.search(sentence):
            return subject
    return "driver"


def detect_conditions(sentence: str) -> list[ConditionLiteral]:
    found: dict[str, ConditionLiteral] = {}
    for pattern, literal in TRIGGER_PATTERNS:
        if pattern.search(sentence):
            found[literal.name] = literal
    return list(found.values())


def extract_logic_atoms_from_section(section: Section) -> list[LogicAtom]:
    atoms: list[LogicAtom] = []
    heading_conditions = detect_conditions(section.heading)
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(section.text) if s.strip()]
    for idx, sentence in enumerate(sentences, start=1):
        modality = detect_modality(sentence)
        if modality is None:
            continue
        refs = find_section_references(sentence)
        merged_conditions: dict[str, ConditionLiteral] = {
            literal.name: literal for literal in heading_conditions
        }
        for literal in detect_conditions(sentence):
            merged_conditions[literal.name] = literal
        atoms.append(
            LogicAtom(
                rule_id=f"TLL_{section.number}_{idx}",
                subject=detect_subject(sentence),
                action=detect_action(sentence),
                modality=modality,  # type: ignore[arg-type]
                conditions=list(merged_conditions.values()),
                references=refs,
                source_section=section.number,
                source_text=sentence,
            )
        )
    return atoms


def extract_logic_atoms(
    sections: list[Section], chapter_filter: str | None = None
) -> list[LogicAtom]:
    atoms: list[LogicAtom] = []
    for section in sections:
        if chapter_filter is not None and section.chapter != chapter_filter:
            continue
        atoms.extend(extract_logic_atoms_from_section(section))
    return atoms


def extract_logic_atoms_from_text(text: str, chapter_filter: str | None = None) -> list[LogicAtom]:
    sections = split_into_sections(text)
    return extract_logic_atoms(sections, chapter_filter=chapter_filter)
