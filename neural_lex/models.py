from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Modality = Literal["must", "must_not", "may"]


@dataclass(frozen=True)
class ConditionLiteral:
    name: str
    value: bool = True

    @classmethod
    def parse(cls, token: str) -> "ConditionLiteral":
        token = token.strip()
        if token.startswith("!"):
            return cls(name=token[1:], value=False)
        lowered = token.lower()
        if lowered.startswith("not "):
            return cls(name=token[4:].strip(), value=False)
        return cls(name=token, value=True)

    def as_token(self) -> str:
        return self.name if self.value else f"!{self.name}"


@dataclass
class Section:
    number: str
    heading: str
    text: str
    chapter: str | None = None


@dataclass
class LogicAtom:
    rule_id: str
    subject: str
    action: str
    modality: Modality
    conditions: list[ConditionLiteral] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    source_section: str | None = None
    source_text: str | None = None
    priority: int = 0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LogicAtom":
        raw_conditions: list[str] = []
        if "conditions" in raw and raw["conditions"] is not None:
            raw_conditions.extend(raw["conditions"])
        trigger = raw.get("trigger")
        if trigger:
            if isinstance(trigger, str):
                raw_conditions.append(trigger)
            elif isinstance(trigger, list):
                raw_conditions.extend(trigger)

        obligation = raw.get("obligation")
        action = raw.get("action") or obligation or "comply"
        modality = raw.get("modality")
        if modality is None:
            modality = "must"
        if modality not in ("must", "must_not", "may"):
            raise ValueError(f"Unsupported modality: {modality}")

        references = raw.get("references") or []

        return cls(
            rule_id=raw["rule_id"],
            subject=raw.get("subject", "driver"),
            action=action,
            modality=modality,
            conditions=[ConditionLiteral.parse(token) for token in raw_conditions],
            references=list(references),
            source_section=raw.get("source_section"),
            source_text=raw.get("source_text"),
            priority=int(raw.get("priority", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "subject": self.subject,
            "action": self.action,
            "modality": self.modality,
            "conditions": [c.as_token() for c in self.conditions],
            "references": self.references,
            "source_section": self.source_section,
            "source_text": self.source_text,
            "priority": self.priority,
        }


@dataclass
class Conflict:
    rule_a: str
    rule_b: str
    reason: str
