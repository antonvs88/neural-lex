# Neural Lex Core Implementation

This directory contains the core logic for the neuro-symbolic legal extraction and verification system.

## Modules

- `models.py`: Defines the foundational data structures:
  - `LogicAtom`: The symbolic representation of a legal rule.
  - `Section`: A parsed unit of legal text.
  - `ConditionLiteral`: Predicates extracted from rules.
- `extractor.py`: Heuristic-based rule extraction using Finnish language regex patterns.
- `llm_extractor.py`: Experimental recursive LLM extraction layer based on the "Recursive Language Model" concept.
- `recursive.py`: Logic for resolving cross-section references (e.g., following §-tags) to build dependency graphs.
- `symbolic.py`: The reasoning engine. Compiles `LogicAtom` objects into SMT/SAT constraints for the Z3 solver or a lightweight fallback.
- `finlex.py`: Utilities for fetching and parsing legal statutes from the Finnish Finlex service.
- `cli.py`: The main command-line entry point.

## Architecture

The system follows a pipeline approach:
1.  **Ingestion** (`finlex.py`) -> `Section` objects.
2.  **Extraction** (`extractor.py` or `llm_extractor.py`) -> `LogicAtom` objects.
3.  **Resolution** (`recursive.py`) -> Enriched dependency map.
4.  **Verification** (`symbolic.py`) -> Conflict & Satisfiability reports.
