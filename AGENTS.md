# Agentic Architecture: Recursive Language Models in Legal Tech

This project implements an experimental extraction layer inspired by the **Recursive Language Model (RLM)** concept, as described by Pietro Bolcato.

## The Problem: Document Complexity
Legal statutes are inherently hierarchical and cross-referenced. A single section (e.g., §18) might be modified or overridden by another (§24). Standard LLM context windows often lose track of these relationships when processing large documents linearly.

## Our Solution: Context-as-State
Instead of feeding the entire law into an LLM, `neural-lex` treats the law as a navigable environment.

### 1. Hierarchical Decomposition
The `RecursiveLLMExtractor` breaks the law into its natural parts: Chapters and Sections. This keeps the "Effective Context Window" small and focused for each individual LLM call.

### 2. Recursive Primitive
When the extractor identifies a section reference (e.g., §18 referencing §24 for priority rules), it executes a **recursive query**:
1.  Pause processing of §18.
2.  Locate and process the referenced §24.
3.  Retrieve the logic atoms extracted from §24.
4.  Inject those atoms back into the context for final resolution of §18 obligations.

### 3. Caching & State
To avoid $O(N^2)$ LLM costs, we maintain a cache of processed sections. This matches the "Context-as-State" principle where the system state evolves as it "reads" the law.

## Future Agentic Roadmap
- **Self-Correction**: Agents that detect conflicts in their own symbolic output and "backtrack" to refine the natural language extraction.
- **Reference Resolution Agents**: Specialized agents that only focus on the *relationship* between sections (e.g., "Does this section narrow or expand the previous one?").

## References
- [Recursive Language Models: Infinite Context that works](https://medium.com/@pietrobolcato/recursive-language-models-infinite-context-that-works-174da45412ab)
