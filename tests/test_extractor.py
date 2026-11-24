from tests.helpers import is_remediation_prompt
import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from proj_sec.common import MODEL_ID, load_kdes
from proj_sec.extractor import extract_kdes, validate_documents, write_llm_log
from proj_sec.pdfio import Section, split_sections
from proj_sec.prompts import chain_of_thought_prompt, few_shot_prompt, zero_shot_prompt
from tests.helpers import TEXT, make_pdf


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pdf = self.root / "cis.pdf"
        make_pdf(self.pdf, TEXT)
        self.section = Section("4.1", "Create a user", "Run as a non-root user.")

    def test_validate_documents(self):
        first, second = validate_documents(self.pdf, self.pdf)
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.pages, 1)
        with self.assertRaises(ValueError):
            validate_documents(self.root / "missing.pdf", self.pdf)

    def test_zero_shot_prompt(self):
        prompt = zero_shot_prompt(self.section)
        self.assertIn(self.section.text, prompt)
        self.assertNotIn("Example 1", prompt)

    def test_few_shot_prompt(self):
        prompt = few_shot_prompt(self.section)
        self.assertIn("Example 1 (synthetic)", prompt)
        self.assertIn("Example 2 (synthetic)", prompt)
        self.assertIn(self.section.text, prompt)

    def test_chain_of_thought_prompt(self):
        prompt = chain_of_thought_prompt(self.section)
        self.assertIn("Analyze in stages", prompt)
        self.assertIn("Return only the final JSON", prompt)
        self.assertIn(self.section.text, prompt)

    def test_extract_kdes(self):
        documents = validate_documents(self.pdf, self.pdf)
        calls = []
        def generate(prompt):
            calls.append(prompt)
            name = prompt.split("Element name: ")[-1].split("\n")[0]
            requirement = "Containers should run as a non-root user." if "4.1\n" in prompt else "Use COPY for local files."
            remediation = "Set USER app." if "4.1\n" in prompt else "Replace ADD with COPY."
            return json.dumps({"name": name, "requirements": [remediation if is_remediation_prompt(prompt) else requirement]})
        output = self.root / "output"
        results = extract_kdes(documents, output, generate, model_identity="unit-test-double")
        self.assertEqual(set(results), {"zero-shot", "few-shot", "chain-of-thought"})
        self.assertEqual(len(calls), 12)  # Two recommendations, two source blocks, three styles; right document cached.
        for pair in results.values():
            self.assertNotEqual(pair[0], pair[1])
            self.assertEqual(load_kdes(pair[0]), load_kdes(pair[1]))
        self.assertTrue((output / "PROMPT.md").is_file())

    def test_write_llm_log(self):
        path = write_llm_log([{"model": MODEL_ID, "prompt": "test prompt", "prompt_type": "few-shot",
                               "output": "raw response"}], self.root / "llm.txt")
        text = path.read_text()
        for label in ("*LLM Name*", "*Prompt Used*", "*Prompt Type*", "*LLM Output*"):
            self.assertIn(label, text)
        self.assertIn("raw response", text)

    def test_section_parser_avoids_controls_table_number(self):
        sections = split_sections(validate_documents(self.pdf, self.pdf)[0])
        self.assertEqual([s.cis_id for s in sections], ["4.1", "4.9"])
        self.assertEqual(sections[1].title, "Ensure that COPY is used instead of ADD in Dockerfiles")

    def test_invalid_model_output_fails_and_logs(self):
        documents = validate_documents(self.pdf, self.pdf)
        output = self.root / "invalid"
        with self.assertRaisesRegex(ValueError, "excerpt numbers"):
            extract_kdes(documents, output, lambda prompt: "broken", retries=0)
        self.assertIn("broken", (output / "llm-output.txt").read_text())
        self.assertFalse(list(output.rglob("*-kdes.yaml")))

    def test_hallucinated_requirement_is_rejected(self):
        documents = validate_documents(self.pdf, self.pdf)
        def generate(prompt):
            name = prompt.split("Element name: ")[-1].split("\n")[0]
            return json.dumps({"name": name, "requirements": ["Invented requirement."]})
        with self.assertRaisesRegex(ValueError, "matching source excerpt"):
            extract_kdes(documents, self.root / "invented", generate, retries=0)

    def test_retry_changes_prompt_and_records_correction(self):
        documents = validate_documents(self.pdf, self.pdf)
        calls = []
        def generate(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return "broken"
            name = prompt.split("Element name: ")[-1].split("\n")[0]
            requirement = "Containers should run as a non-root user." if "4.1\n" in prompt else "Use COPY for local files."
            remediation = "Set USER app." if "4.1\n" in prompt else "Replace ADD with COPY."
            return json.dumps({"name": name, "requirements": [remediation if is_remediation_prompt(prompt) else requirement]})
        output = self.root / "retried"
        extract_kdes(documents, output, generate, prompt_types=("zero-shot",))
        self.assertIn("Correction required", calls[1])
        self.assertIn("Correction required", (output / "PROMPT.md").read_text())

    def test_empty_and_encrypted_pdf_rejected(self):
        blank = self.root / "blank.pdf"
        writer = PdfWriter(); writer.add_blank_page(width=612, height=792); writer.write(blank)
        with self.assertRaisesRegex(ValueError, "No extractable text"):
            validate_documents(blank, blank)
        writer.encrypt("secret"); writer.write(blank)
        with self.assertRaisesRegex(ValueError, "Encrypted"):
            validate_documents(blank, blank)

    def test_shared_cache_reuses_calls_across_pair_directories(self):
        documents = validate_documents(self.pdf, self.pdf)
        calls = []
        def generate(prompt):
            calls.append(prompt)
            name = prompt.split('Element name: ')[-1].split('\n')[0]
            requirement = 'Containers should run as a non-root user.' if '4.1\n' in prompt else 'Use COPY for local files.'
            remediation = 'Set USER app.' if '4.1\n' in prompt else 'Replace ADD with COPY.'
            return json.dumps({'name': name, 'requirements': [remediation if is_remediation_prompt(prompt) else requirement]})
        shared = self.root / 'shared-cache'
        first = extract_kdes(documents, self.root / 'first', generate, cache_dir=shared,
                             prompt_types=('zero-shot',), model_identity='same-model')
        extract_kdes(documents, self.root / 'second', generate, cache_dir=shared,
                     prompt_types=('zero-shot',), model_identity='same-model')
        self.assertEqual(len(calls), 4)
        extract_kdes(documents, self.root / 'third', generate, cache_dir=shared,
                     prompt_types=('zero-shot',), model_identity='different-model')
        self.assertEqual(len(calls), 8)
