# Tests

This directory contains the test suite for `neural-lex`.

## Test Modules

- `test_symbolic.py`: Verifies the symbolic reasoning backend (Z3/Fallback), including conflict detection and scenario satisfiability.
- `test_llm_extractor.py`: Verifies the recursive LLM extraction logic using a mock provider.

## Running Tests

From the project root, run:

```bash
python -m unittest discover tests
```

Or if you have `pytest` installed:

```bash
pytest
```
