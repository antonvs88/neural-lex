# Examples

This directory contains sample inputs for the `neural-lex` system.

## Files

- `tll_ch2_excerpt.txt`: A plain-text excerpt from Chapter 2 of the Finnish Traffic Law (Tieliikennelaki).
- `tll_intersection_atoms.json`: Pre-extracted `LogicAtom` objects representing intersection rules. This is used for benchmarking symbolic reasoning without running the extraction layer.

## Usage

To run the CLI on these examples:

```bash
# Using pre-extracted atoms
python -m neural_lex.cli --atoms-json examples/tll_intersection_atoms.json

# Extracting from the text excerpt
python -m neural_lex.cli --text-file examples/tll_ch2_excerpt.txt --chapter 2
```
