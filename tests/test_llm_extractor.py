import unittest
from neural_lex.llm_extractor import RecursiveLLMExtractor, LLMProvider
from neural_lex.models import LogicAtom, Section

class MockProvider(LLMProvider):
    def __init__(self):
        self.responses = {
            "18": {
                "atoms": [
                    {
                        "rule_id": "TLL_18_1",
                        "subject": "driver",
                        "action": "yield",
                        "modality": "must",
                        "conditions": ["approaching_intersection", "coming_from_right"],
                        "references": ["24"],
                        "source_section": "18",
                        "source_text": "Driver must yield to right."
                    }
                ]
            },
            "24": {
                "atoms": [
                    {
                        "rule_id": "TLL_24_1",
                        "subject": "driver",
                        "action": "proceed",
                        "modality": "may",
                        "conditions": ["has_priority_sign"],
                        "references": [],
                        "source_section": "24",
                        "source_text": "Driver may proceed if priority sign."
                    }
                ]
            }
        }

    def query(self, prompt: str, system_prompt: str | None = None) -> str:
        # Simple hack to find which section we are querying
        import json
        for sec_num, resp in self.responses.items():
            if f"Section {sec_num}:" in prompt:
                return json.dumps(resp)
        return json.dumps({"atoms": []})

class TestRecursiveExtractor(unittest.TestCase):
    def test_recursive_caching(self):
        provider = MockProvider()
        extractor = RecursiveLLMExtractor(provider)
        
        sections = [
            Section(number="18", heading="Yielding", text="Driver must yield to right. See section 24."),
            Section(number="24", heading="Priority", text="Driver may proceed if priority sign.")
        ]
        
        # This should trigger recursive call to section 24 when processing 18
        atoms_18 = extractor.extract_recursive(sections[0], sections)
        
        self.assertEqual(len(atoms_18), 1)
        self.assertEqual(atoms_18[0].rule_id, "TLL_18_1")
        
        # Check if 24 is in cache
        self.assertIn("24", extractor.cache)
        self.assertEqual(len(extractor.cache["24"]), 1)
        self.assertEqual(extractor.cache["24"][0].rule_id, "TLL_24_1")

if __name__ == "__main__":
    unittest.main()
