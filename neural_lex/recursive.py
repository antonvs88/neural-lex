from __future__ import annotations

from collections import deque

from .models import LogicAtom


def build_section_rule_index(atoms: list[LogicAtom]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for atom in atoms:
        if atom.source_section is None:
            continue
        index.setdefault(atom.source_section, []).append(atom.rule_id)
    return index


def resolve_rule_references(
    atoms: list[LogicAtom], max_depth: int = 3
) -> dict[str, set[str]]:
    section_index = build_section_rule_index(atoms)
    rule_by_id = {atom.rule_id: atom for atom in atoms}
    resolved: dict[str, set[str]] = {}

    for atom in atoms:
        discovered: set[str] = set()
        queue: deque[tuple[str, int]] = deque((ref, 1) for ref in atom.references)
        seen_sections: set[str] = set()

        while queue:
            section_ref, depth = queue.popleft()
            if section_ref in seen_sections or depth > max_depth:
                continue
            seen_sections.add(section_ref)
            for linked_rule_id in section_index.get(section_ref, []):
                discovered.add(linked_rule_id)
                linked_rule = rule_by_id.get(linked_rule_id)
                if linked_rule is None:
                    continue
                for nested_ref in linked_rule.references:
                    queue.append((nested_ref, depth + 1))
        resolved[atom.rule_id] = discovered
    return resolved
