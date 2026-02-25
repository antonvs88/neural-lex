from __future__ import annotations

import re
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

from .models import Section

CHAPTER_PATTERNS = [
    re.compile(r"^\s*Luku\s+(\d+)\b(?:\s*[-–:]\s*(.+))?\s*$", flags=re.IGNORECASE),
    re.compile(r"^\s*(\d+)\s+luku\b(?:\s*[-–:]\s*(.+))?\s*$", flags=re.IGNORECASE),
]
SECTION_PATTERN = re.compile(r"^\s*(\d+[a-zA-Z]?)\s*§\s*(.*)$")
SECTION_REFERENCE_PATTERN = re.compile(r"\b(\d+[a-zA-Z]?)\s*§")


def fetch_finlex_html(url: str, timeout: int = 30) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def finlex_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    root = main if main is not None else soup
    return root.get_text("\n")


def split_into_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    chapter: str | None = None
    chapter_heading = ""
    current_number: str | None = None
    current_heading = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_number, current_heading, current_lines
        if current_number is None:
            return
        body = "\n".join(line.rstrip() for line in current_lines).strip()
        heading = current_heading.strip()
        if chapter_heading:
            heading = f"{heading} ({chapter_heading})".strip()
        sections.append(
            Section(
                number=current_number,
                heading=heading,
                text=body,
                chapter=chapter,
            )
        )
        current_number = None
        current_heading = ""
        current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_number is not None:
                current_lines.append("")
            continue

        chapter_match = None
        for pattern in CHAPTER_PATTERNS:
            chapter_match = pattern.match(line)
            if chapter_match:
                chapter = chapter_match.group(1)
                chapter_heading = chapter_match.group(2) or ""
                break
        if chapter_match:
            continue

        section_match = SECTION_PATTERN.match(line)
        if section_match:
            flush()
            current_number = section_match.group(1)
            current_heading = section_match.group(2) or ""
            continue

        if current_number is not None:
            current_lines.append(line)

    flush()
    return sections


def find_section_references(text: str) -> list[str]:
    refs = []
    for match in SECTION_REFERENCE_PATTERN.finditer(text):
        ref = match.group(1)
        if ref not in refs:
            refs.append(ref)
    return refs


def group_sections_by_chapter(sections: list[Section]) -> dict[str, list[Section]]:
    grouped: dict[str, list[Section]] = defaultdict(list)
    for section in sections:
        key = section.chapter or "unknown"
        grouped[key].append(section)
    return dict(grouped)
