from neural_lex.models import LogicAtom
from neural_lex.symbolic import find_pairwise_conflicts


def test_no_conflict_when_conditions_do_not_overlap() -> None:
    atoms = [
        LogicAtom.from_dict(
            {
                "rule_id": "TLL_18",
                "subject": "driver",
                "action": "yield",
                "modality": "must",
                "conditions": [
                    "approaching_intersection",
                    "coming_from_right",
                    "!has_yield_sign",
                ],
            }
        ),
        LogicAtom.from_dict(
            {
                "rule_id": "TLL_24",
                "subject": "driver",
                "action": "yield",
                "modality": "must",
                "conditions": [
                    "approaching_intersection",
                    "has_yield_sign",
                ],
            }
        ),
    ]

    conflicts = find_pairwise_conflicts(atoms)
    assert conflicts == []


def test_conflict_on_incompatible_mandatory_actions() -> None:
    atoms = [
        LogicAtom.from_dict(
            {
                "rule_id": "A",
                "subject": "driver",
                "action": "yield",
                "modality": "must",
                "conditions": ["approaching_intersection", "has_yield_sign"],
            }
        ),
        LogicAtom.from_dict(
            {
                "rule_id": "B",
                "subject": "driver",
                "action": "proceed",
                "modality": "must",
                "conditions": ["approaching_intersection", "has_yield_sign"],
            }
        ),
    ]

    conflicts = find_pairwise_conflicts(atoms)
    assert len(conflicts) == 1
    assert conflicts[0].rule_a == "A"
    assert conflicts[0].rule_b == "B"
