# Technical Documentation: Neural Lex

This document provides a deep dive into the internal logic, schemas, and reasoning processes of the `neural-lex` project.

## Logic Atom Schema

Each extracted rule becomes a `LogicAtom`:

```json
{
  "rule_id": "TLL_18_2",
  "subject": "driver",
  "action": "yield",
  "modality": "must",
  "conditions": ["approaching_intersection", "coming_from_right", "!has_yield_sign"],
  "references": ["24"],
  "source_section": "18",
  "source_text": "Kuljettajan on väistettävä oikealta ...",
  "priority": 0
}
```

### Field semantics

- `rule_id`: Unique ID for traceability.
- `subject`: Actor type (`driver`, `cyclist`, etc.).
- `action`: Canonicalized action (`yield`, `stop`, `proceed`, `comply`...).
- `modality`:
  - `must`: obligation
  - `must_not`: prohibition
  - `may`: permission (currently ignored in hard conflict checks)
- `conditions`: Predicates required for rule activation.
  - Positive: `"has_yield_sign"`
  - Negative: `"!has_yield_sign"`
- `references`: Referenced legal sections (e.g. `"24"` from `"24 §"`).
- `source_section` and `source_text`: provenance.
- `priority`: reserved for future precedence handling.

## How Consistency Checking Works

### Pairwise conflict scan

For each rule pair:

1. Check if conditions can overlap.
2. If overlap exists, test whether obligations are mutually incompatible.

Default incompatible action pairs:

- `yield` vs `proceed`
- `stop` vs `proceed`
- `stop` vs `overtake`

Conflicts are reported with both rule IDs.

### Scenario satisfiability

Given assumptions like:

```text
approaching_intersection=true coming_from_right=true has_yield_sign=true
```

the engine checks whether any assignment satisfies all active obligations under those assumptions.

## Extraction Heuristics (Heuristic Backend)

The default extractor uses Finnish pattern matching for:

- Normative markers (`on ...ttävä`, `pitää`, `tulee`, `ei saa`, `on kielletty`, `saa`, `voi`)
- Action signals (`väist`, `pysäh`, `ohit`, `käänt`, `ajaa/jatkaa`)
- Trigger signals (`ristey...`, `oikealta`, `väistämismerkki`, `liikennevalo`, etc.)
- Subject hints (`kuljettaja`, `polkupyöräilijä`, `jalankulkija`, `raitiovaunun kuljettaja`)

## Recursive Reference Resolution

`resolve_rule_references()` builds a section-to-rule index and walks references breadth-first up to a max depth (default `3`), enabling basic "except as in §X" chain discovery.

## CLI Detailed Reference

```text
python -m neural_lex.cli
  (--atoms-json PATH | --text-file PATH | --finlex-url URL)
  [--chapter N]
  [--show-atoms]
  [--dump-atoms PATH]
  [--scenario key=value [key=value ...]]
  [--use-llm]
  [--gemini]
  [--openai-key KEY]
  [--google-key KEY]
```

## Troubleshooting

### `z3-solver` build failure on macOS/Apple Silicon

If you see `Failed building wheel for z3-solver` and a long C++ build traceback:

1. Use the base install (`pip install -e ".[dev]"`) and continue with fallback backend.
2. Force wheel-only install: `pip install --only-binary=:all: z3-solver`

## References

### Legal Sources (Finlex)

- Tieliikennelaki 729/2018: https://www.finlex.fi/fi/laki/smur/2018/20180729
- Statute Book, English: https://www.finlex.fi/en/legislation/collection/2018/729

### Symbolic Reasoning

- Online Z3 Guide: https://microsoft.github.io/z3guide/
- SMT-LIB standard: https://smt-lib.org/
