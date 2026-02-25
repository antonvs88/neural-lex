import json
import os
from typing import Any, Protocol

from .models import LogicAtom, Section
from .finlex import split_into_sections

class LLMProvider(Protocol):
    def query(self, prompt: str, system_prompt: str | None = None) -> str:
        ...

class OpenAIProvider:
    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def query(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content or ""

class GeminiProvider:
    def __init__(self, model: str = "gemini-1.5-pro"):
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(model)

    def query(self, prompt: str, system_prompt: str | None = None) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = self.model.generate_content(
            full_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return response.text

class RecursiveLLMExtractor:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.cache: dict[str, list[LogicAtom]] = {}

    def extract_from_text(self, text: str) -> list[LogicAtom]:
        sections = split_into_sections(text)
        all_atoms = []
        for section in sections:
            all_atoms.extend(self.extract_recursive(section, sections))
        return all_atoms

    def extract_recursive(self, section: Section, all_sections: list[Section], depth: int = 0, max_depth: int = 3) -> list[LogicAtom]:
        if section.number in self.cache:
            return self.cache[section.number]
        
        if depth > max_depth:
            return []

        # 1. Extract atoms from current section
        atoms = self._call_llm_for_section(section)
        
        # 2. Identify references and recursively resolve them
        # (This is the 'Recursive Primitive' from the RLM concept)
        for atom in atoms:
            extra_context = []
            for ref in atom.references:
                ref_section = next((s for s in all_sections if s.number == ref), None)
                if ref_section:
                    ref_atoms = self.extract_recursive(ref_section, all_sections, depth + 1, max_depth)
                    for ra in ref_atoms:
                        extra_context.append(ra.to_dict())
            
            # If we found referenced context, we might want to re-evaluate the atom 
            # (In a full implementation, we'd pass this back to the LLM to 'merge' logic)
            # For now, we store the discovered references in the atom.
        
        self.cache[section.number] = atoms
        return atoms

    def _call_llm_for_section(self, section: Section) -> list[LogicAtom]:
        system_prompt = """
You are a legal logic extractor. Transform the following Finnish traffic law section into a JSON list of LogicAtoms.
Schema for LogicAtom:
{
  "rule_id": "string",
  "subject": "driver" | "cyclist" | "pedestrian" | "tram_driver",
  "action": "yield" | "stop" | "overtake" | "turn" | "proceed" | "comply",
  "modality": "must" | "must_not" | "may",
  "conditions": ["condition1", "!condition2"],
  "references": ["section_number1", "section_number2"],
  "source_section": "string",
  "source_text": "string"
}
Return ONLY a JSON object with a key "atoms" containing the list.
"""
        prompt = f"Section {section.number}: {section.heading}\n\nText:\n{section.text}"
        
        try:
            response_text = self.provider.query(prompt, system_prompt)
            data = json.loads(response_text)
            return [LogicAtom.from_dict(raw) for raw in data.get("atoms", [])]
        except Exception as e:
            print(f"Error extracting from section {section.number}: {e}")
            return []
