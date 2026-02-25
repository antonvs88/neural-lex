from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extractor import extract_logic_atoms_from_text
from .finlex import fetch_finlex_html, finlex_html_to_text
from .models import LogicAtom
from .recursive import resolve_rule_references
from .symbolic import check_scenario, find_pairwise_conflicts, symbolic_backend_name


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "t", "yes", "y"}:
        return True
    if lowered in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Not a boolean value: {value}")


def _parse_scenario(items: list[str] | None) -> dict[str, bool]:
    if not items:
        return {}
    assumptions: dict[str, bool] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Scenario assumption must look like key=true: {item}")
        key, value = item.split("=", 1)
        assumptions[key.strip()] = _parse_bool(value)
    return assumptions


def _load_atoms_from_json(path: Path) -> list[LogicAtom]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("JSON must be a list of rule objects")
    return [LogicAtom.from_dict(item) for item in raw]


def _load_atoms_from_source(args: argparse.Namespace) -> list[LogicAtom]:
    if args.atoms_json:
        return _load_atoms_from_json(Path(args.atoms_json))

    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
        chapter = str(args.chapter) if args.chapter is not None else None
        return extract_logic_atoms_from_text(text, chapter_filter=chapter)

    html = fetch_finlex_html(args.finlex_url)
    text = finlex_html_to_text(html)
    chapter = str(args.chapter) if args.chapter is not None else None
    return extract_logic_atoms_from_text(text, chapter_filter=chapter)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neural-lex",
        description="Extract legal logic atoms and check for symbolic conflicts with Z3",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--atoms-json", help="Path to JSON list of logic atoms")
    source.add_argument("--text-file", help="Path to plain-text legal source")
    source.add_argument("--finlex-url", help="Finlex URL for source law page")
    parser.add_argument("--chapter", type=int, help="Only extract this chapter number")
    parser.add_argument("--show-atoms", action="store_true", help="Print extracted atoms")
    parser.add_argument(
        "--dump-atoms",
        help="Write extracted atoms to JSON file",
    )
    parser.add_argument(
        "--scenario",
        nargs="*",
        help="Scenario assumptions, e.g. approaching_intersection=true has_yield_sign=false",
    )
    args = parser.parse_args()

    atoms = _load_atoms_from_source(args)
    print(f"Extracted atoms: {len(atoms)}")
    print(f"Symbolic backend: {symbolic_backend_name()}")

    if args.dump_atoms:
        out = Path(args.dump_atoms)
        out.write_text(
            json.dumps([atom.to_dict() for atom in atoms], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Wrote atoms to: {out}")

    if args.show_atoms:
        for atom in atoms:
            print(json.dumps(atom.to_dict(), ensure_ascii=False))

    resolved = resolve_rule_references(atoms, max_depth=3)
    referenced_count = sum(1 for items in resolved.values() if items)
    print(f"Rules with recursive references resolved: {referenced_count}")

    conflicts = find_pairwise_conflicts(atoms)
    if conflicts:
        print(f"Conflicts found: {len(conflicts)}")
        for conflict in conflicts:
            print(f"- {conflict.rule_a} vs {conflict.rule_b}: {conflict.reason}")
    else:
        print("No pairwise conflicts found.")

    assumptions = _parse_scenario(args.scenario)
    if assumptions:
        consistent, model = check_scenario(atoms, assumptions)
        if consistent:
            print("Scenario satisfiable.")
            print(model)
        else:
            print("Scenario inconsistent.")


if __name__ == "__main__":
    main()
