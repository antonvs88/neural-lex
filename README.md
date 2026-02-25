# neural-lex

`neural-lex` is a neuro-symbolic prototype for extracting legal rules from text and checking logical consistency with a SAT/SMT-style backend.

The current implementation is tuned for modular traffic-law text (for example **Tieliikennelaki 729/2018**) where general rules, sign-based overrides, and section references interact.

## What This Project Does

1. Parses legal source text (plain text or Finlex HTML).
2. Splits text into chapters and sections.
3. Extracts "logic atoms" from normative sentences (`must`, `must_not`, `may`).
4. Resolves cross-section references recursively (depth-limited).
5. Compiles rules into symbolic constraints.
6. Runs:
   - Pairwise conflict detection.
   - Scenario satisfiability checks.

## Why Neuro-Symbolic for Traffic Law

- Natural-language rules are extracted from legal text (neural/extraction layer).
- Final reasoning is done on symbols, not prose (symbolic verification layer).
- This reduces hallucination risk in edge-case Q&A because conclusions are tied to formalized rules and conditions.

## Current Status

- Baseline implementation is working end-to-end.
- Extraction is heuristic/rule-based (regex patterns), not an LLM pipeline yet.
- Z3 is optional; a lightweight fallback evaluator is used when `z3-solver` is unavailable.

## Repository Layout

```text
neural_lex/
  cli.py         # CLI entry point
  models.py      # LogicAtom, Section, Conflict models
  finlex.py      # Finlex fetch + HTML/text + section splitting
  extractor.py   # Rule extraction heuristics
  recursive.py   # Recursive section-reference resolver
  symbolic.py    # Constraint compilation + conflict/scenario checks
examples/
  tll_ch2_excerpt.txt
  tll_intersection_atoms.json
tests/
  test_symbolic.py
```

## Installation

Base install (works without Z3):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional Z3 backend:

```bash
pip install -e ".[solver]"
```

If `z3-solver` fails to compile on your machine, the project still runs with the fallback symbolic backend.

## Quick Start

### 1. Run on predefined atoms

```bash
python -m neural_lex.cli --atoms-json examples/tll_intersection_atoms.json --show-atoms
```

The CLI prints `Symbolic backend: z3` or `Symbolic backend: fallback`.

### 2. Extract from local legal text

```bash
python -m neural_lex.cli \
  --text-file examples/tll_ch2_excerpt.txt \
  --chapter 2 \
  --dump-atoms out_atoms.json \
  --show-atoms
```

### 3. Run a scenario satisfiability query

```bash
python -m neural_lex.cli \
  --atoms-json examples/tll_intersection_atoms.json \
  --scenario approaching_intersection=true coming_from_right=true has_yield_sign=true
```

### 4. Pull source from Finlex directly

```bash
python -m neural_lex.cli \
  --finlex-url "https://www.finlex.fi/fi/laki/alkup/2018/20180729" \
  --chapter 2
```

## CLI Reference

```text
python -m neural_lex.cli
  (--atoms-json PATH | --text-file PATH | --finlex-url URL)
  [--chapter N]
  [--show-atoms]
  [--dump-atoms PATH]
  [--scenario key=value [key=value ...]]
```

### Arguments

- `--atoms-json`: Use pre-extracted atom JSON (fastest for reasoning loops).
- `--text-file`: Extract atoms from local legal text.
- `--finlex-url`: Fetch legal source from Finlex HTML page.
- `--chapter`: Restrict extraction to one chapter (e.g. `2`).
- `--show-atoms`: Print extracted atoms as JSON lines.
- `--dump-atoms`: Save extracted atoms to file.
- `--scenario`: Set predicate assumptions for satisfiability check.

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

## Extraction Heuristics (Current)

The extractor currently uses Finnish pattern matching for:

- Normative markers (`on ...ttävä`, `pitää`, `tulee`, `ei saa`, `on kielletty`, `saa`, `voi`)
- Action signals (`väist`, `pysäh`, `ohit`, `käänt`, `ajaa/jatkaa`)
- Trigger signals (`ristey...`, `oikealta`, `väistämismerkki`, `liikennevalo`, etc.)
- Subject hints (`kuljettaja`, `polkupyöräilijä`, `jalankulkija`, `raitiovaunun kuljettaja`)

This is intentionally conservative and should be expanded for production use.

## Recursive Reference Resolution

`resolve_rule_references()` builds a section-to-rule index and walks references breadth-first up to a max depth (default `3`), enabling basic "except as in §X" chain discovery.

Current output is a dependency map (`rule_id -> referenced rule_ids`) used for auditability and future precedence merging.

## Testing

Run tests:

```bash
pytest -q
```

Current tests cover:

- No conflict when triggers are mutually exclusive.
- Conflict when overlapping triggers require incompatible actions.

## Troubleshooting

### `z3-solver` build failure on macOS/Apple Silicon

If you see `Failed building wheel for z3-solver` and a long C++ build traceback:

1. Use the base install (`pip install -e ".[dev]"`) and continue with fallback backend.
2. If you require native Z3, force wheel-only install to avoid local compilation:

   ```bash
   pip install --only-binary=:all: z3-solver
   ```

3. If wheel-only install fails, pin to a wheel-published version for your platform:

   ```bash
   pip install --only-binary=:all: "z3-solver==4.12.2.0"
   ```

4. Confirm backend in CLI output (`Symbolic backend: ...`).

## Extending This Project

Recommended next improvements:

1. Add an LLM extractor with JSON schema validation and retry loops.
2. Add legal precedence modeling:
   - signs/control devices over defaults
   - `lex specialis` style overrides
   - explicit `except §X` logic merging
3. Increase coverage of Finnish legal phrasing and condition normalization.
4. Add batch contradiction reports by chapter and section.
5. Add trace output that shows which source rules produced each final obligation.

## Limitations and Disclaimer

- This is a technical prototype, not legal advice.
- Results depend heavily on extraction quality.
- `may` permissions are not fully represented in deontic conflict semantics yet.
- Full legal interpretation requires domain-expert validation and case-context modeling.

## References

### Legal Sources (Finlex)

- Tieliikennelaki 729/2018 (up-to-date, Finnish): https://www.finlex.fi/fi/laki/smur/2018/20180729
- Tieliikennelaki 729/2018 (original statute text): https://www.finlex.fi/fi/laki/alkup/2018/20180729
- Tieliikennelaki 729/2018 (Statute Book, English): https://www.finlex.fi/en/legislation/collection/2018/729
- Vägtrafiklag 729/2018 (up-to-date, Swedish): https://finlex.fi/sv/lagstiftning/2018/729

### Open Data and API

- Finlex Open Data overview: https://www.finlex.fi/en/open-data
- Finlex integration quick guide (REST/OpenAPI usage): https://www.finlex.fi/en/open-data/integration-quick-guide
- Finlex FAQ (includes open-data usage/licensing notes): https://www.finlex.fi/en/faq

### Symbolic Reasoning and Standards

- Online Z3 Guide: https://microsoft.github.io/z3guide/
- Z3 repository (official): https://github.com/Z3Prover/z3
- Programming Z3 tutorial: https://z3prover.github.io/papers/programmingz3.html
- SMT-LIB standard: https://smt-lib.org/

### Python Libraries

- `z3-solver` (PyPI): https://pypi.org/project/z3-solver/
