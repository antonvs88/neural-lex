from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, product
from typing import Any, Iterable

try:
    from z3 import And, Bool, BoolRef, BoolVal, Implies, ModelRef, Not, Solver, sat

    HAVE_Z3 = True
except ModuleNotFoundError:
    BoolRef = Any  # type: ignore[misc,assignment]
    ModelRef = Any  # type: ignore[misc,assignment]
    HAVE_Z3 = False

from .models import Conflict, LogicAtom

DEFAULT_INCOMPATIBLE_ACTIONS = {
    ("yield", "proceed"),
    ("stop", "proceed"),
    ("stop", "overtake"),
}


def symbolic_backend_name() -> str:
    return "z3" if HAVE_Z3 else "fallback"


@dataclass
class SymbolicCompiler:
    predicates: dict[str, BoolRef] = field(default_factory=dict)
    actions: dict[str, BoolRef] = field(default_factory=dict)

    def predicate(self, name: str) -> BoolRef:
        if not HAVE_Z3:
            raise RuntimeError("Z3 is not available")
        if name not in self.predicates:
            self.predicates[name] = Bool(name)
        return self.predicates[name]

    def action(self, name: str) -> BoolRef:
        if not HAVE_Z3:
            raise RuntimeError("Z3 is not available")
        key = f"must_{name}"
        if key not in self.actions:
            self.actions[key] = Bool(key)
        return self.actions[key]

    def condition_expr(self, atom: LogicAtom) -> BoolRef:
        if not HAVE_Z3:
            raise RuntimeError("Z3 is not available")
        clauses: list[BoolRef] = []
        for literal in atom.conditions:
            predicate = self.predicate(literal.name)
            clauses.append(predicate if literal.value else Not(predicate))
        if not clauses:
            return BoolVal(True)
        return And(clauses)

    def requirement_expr(self, atom: LogicAtom) -> BoolRef | None:
        if atom.modality == "may":
            return None
        if not HAVE_Z3:
            raise RuntimeError("Z3 is not available")
        action = self.action(atom.action)
        if atom.modality == "must":
            return action
        if atom.modality == "must_not":
            return Not(action)
        return None


def _normalize_pairs(pairs: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    normalized: set[tuple[str, str]] = set()
    for left, right in pairs:
        if left == right:
            continue
        if left < right:
            normalized.add((left, right))
        else:
            normalized.add((right, left))
    return normalized


def _add_incompatible_action_constraints(
    solver: Any,
    compiler: SymbolicCompiler,
    incompatible_actions: set[tuple[str, str]],
) -> None:
    if not HAVE_Z3:
        raise RuntimeError("Z3 is not available")
    for left, right in incompatible_actions:
        solver.add(Not(And(compiler.action(left), compiler.action(right))))


def _condition_overlap(atom_a: LogicAtom, atom_b: LogicAtom) -> bool:
    values: dict[str, bool] = {}
    for literal in [*atom_a.conditions, *atom_b.conditions]:
        if literal.name in values and values[literal.name] != literal.value:
            return False
        values[literal.name] = literal.value
    return True


def _requirement_signature(atom: LogicAtom) -> tuple[str, bool] | None:
    if atom.modality == "may":
        return None
    if atom.modality == "must":
        return atom.action, True
    if atom.modality == "must_not":
        return atom.action, False
    return None


def _requirements_conflict(
    requirement_a: tuple[str, bool],
    requirement_b: tuple[str, bool],
    incompatible_actions: set[tuple[str, str]],
) -> bool:
    action_a, positive_a = requirement_a
    action_b, positive_b = requirement_b
    if action_a == action_b and positive_a != positive_b:
        return True
    if positive_a and positive_b:
        key = (action_a, action_b) if action_a < action_b else (action_b, action_a)
        return key in incompatible_actions
    return False


def build_solver(
    atoms: list[LogicAtom],
    incompatible_actions: set[tuple[str, str]] | None = None,
) -> tuple[Any, SymbolicCompiler]:
    if not HAVE_Z3:
        raise RuntimeError("z3-solver is not installed; install it to build the native solver.")
    pairs = _normalize_pairs(incompatible_actions or DEFAULT_INCOMPATIBLE_ACTIONS)
    compiler = SymbolicCompiler()
    solver = Solver()
    _add_incompatible_action_constraints(solver, compiler, pairs)

    for atom in atoms:
        req = compiler.requirement_expr(atom)
        if req is None:
            continue
        solver.add(Implies(compiler.condition_expr(atom), req))

    return solver, compiler


def check_scenario(
    atoms: list[LogicAtom], assumptions: dict[str, bool]
) -> tuple[bool, ModelRef | None]:
    if HAVE_Z3:
        solver, compiler = build_solver(atoms)
        for predicate_name, value in assumptions.items():
            predicate = compiler.predicate(predicate_name)
            solver.add(predicate if value else Not(predicate))

        if solver.check() == sat:
            return True, solver.model()
        return False, None

    incompatible = _normalize_pairs(DEFAULT_INCOMPATIBLE_ACTIONS)
    predicates = {literal.name for atom in atoms for literal in atom.conditions}
    unknown = sorted(predicates - set(assumptions.keys()))
    for values in product([False, True], repeat=len(unknown)):
        model = dict(assumptions)
        model.update(dict(zip(unknown, values)))
        action_constraints: dict[str, bool] = {}
        consistent = True
        for atom in atoms:
            if atom.modality == "may":
                continue
            if not all(model.get(literal.name, False) == literal.value for literal in atom.conditions):
                continue
            needed = atom.modality == "must"
            if atom.action in action_constraints and action_constraints[atom.action] != needed:
                consistent = False
                break
            action_constraints[atom.action] = needed

        if not consistent:
            continue

        for left, right in incompatible:
            if action_constraints.get(left) is True and action_constraints.get(right) is True:
                consistent = False
                break
        if consistent:
            model.update({f"must_{k}": v for k, v in action_constraints.items()})
            return True, model
    return False, None


def find_pairwise_conflicts(
    atoms: list[LogicAtom],
    incompatible_actions: set[tuple[str, str]] | None = None,
) -> list[Conflict]:
    pairs = _normalize_pairs(incompatible_actions or DEFAULT_INCOMPATIBLE_ACTIONS)
    conflicts: list[Conflict] = []

    if HAVE_Z3:
        compiler = SymbolicCompiler()
        for atom_a, atom_b in combinations(atoms, 2):
            req_a = compiler.requirement_expr(atom_a)
            req_b = compiler.requirement_expr(atom_b)
            if req_a is None or req_b is None:
                continue

            cond_a = compiler.condition_expr(atom_a)
            cond_b = compiler.condition_expr(atom_b)

            overlap_solver = Solver()
            _add_incompatible_action_constraints(overlap_solver, compiler, pairs)
            overlap_solver.add(cond_a)
            overlap_solver.add(cond_b)
            if overlap_solver.check() != sat:
                continue

            conflict_solver = Solver()
            _add_incompatible_action_constraints(conflict_solver, compiler, pairs)
            conflict_solver.add(cond_a)
            conflict_solver.add(cond_b)
            conflict_solver.add(req_a)
            conflict_solver.add(req_b)

            if conflict_solver.check() != sat:
                conflicts.append(
                    Conflict(
                        rule_a=atom_a.rule_id,
                        rule_b=atom_b.rule_id,
                        reason="Mutually exclusive obligations under overlapping triggers",
                    )
                )
        return conflicts

    for atom_a, atom_b in combinations(atoms, 2):
        requirement_a = _requirement_signature(atom_a)
        requirement_b = _requirement_signature(atom_b)
        if requirement_a is None or requirement_b is None:
            continue
        if not _condition_overlap(atom_a, atom_b):
            continue
        if _requirements_conflict(requirement_a, requirement_b, pairs):
            conflicts.append(
                Conflict(
                    rule_a=atom_a.rule_id,
                    rule_b=atom_b.rule_id,
                    reason="Mutually exclusive obligations under overlapping triggers",
                )
            )

    return conflicts
