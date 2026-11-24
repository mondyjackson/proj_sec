import csv
import tempfile
import unittest
from pathlib import Path

import yaml

from proj_sec.common import NO_NAMES, NO_REQUIREMENTS
from proj_sec.comparator import compare_names, compare_requirements, load_yaml_pair


def document(name="Protect data", requirements=None):
    return {"element1": {"name": name, "requirements": requirements or ["Encrypt data."]}}


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_load_yaml_pair(self):
        path = self.root / "input.yaml"
        path.write_text(yaml.safe_dump(document()))
        self.assertEqual(load_yaml_pair(path, path), (document(), document()))

    def test_compare_names(self):
        path = compare_names((document("Old name"), document("New name")), self.root / "names.txt")
        with path.open(newline="") as stream:
            self.assertEqual({row[0] for row in csv.reader(stream)}, {"Old name", "New name"})

    def test_compare_requirements(self):
        pair = (document(requirements=["Keep A.", "Remove B, C."]),
                document(requirements=["Keep A.", "Add D."]))
        path = compare_requirements(pair, self.root / "requirements.txt")
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows, [["Protect data", "Add D."], ["Protect data", "Remove B, C."]])

    def test_identical_and_reordered_documents_have_no_changes(self):
        left = document(" Protect  data ", ["Keep A.", "Keep B."])
        right = document("protect data", ["Keep B.", "Keep   A."])
        self.assertEqual(compare_names((left, right), self.root / "names.txt").read_text().strip(), NO_NAMES)
        self.assertEqual(compare_requirements((left, right), self.root / "req.txt").read_text().strip(), NO_REQUIREMENTS)

    def test_removed_element_requirements_are_reported(self):
        output = compare_requirements((document(), {}), self.root / "removed.txt")
        self.assertIn("Encrypt data.", output.read_text())

    def test_duplicate_yaml_keys_and_aliases_rejected(self):
        path = self.root / "bad.yaml"
        for text in ("element1: {}\nelement1: {}\n", "element1: &shared {}\nelement2: *shared\n"):
            path.write_text(text)
            with self.assertRaises(ValueError):
                load_yaml_pair(path, path)

    def test_command_case_is_not_erased(self):
        pair = (document(requirements=["Set USER app."]), document(requirements=["Set user app."]))
        self.assertNotEqual(compare_requirements(pair, self.root / "case.txt").read_text().strip(), NO_REQUIREMENTS)
