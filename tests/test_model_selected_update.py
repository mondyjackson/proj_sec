import tempfile
import unittest
from pathlib import Path

from scripts.apply_model_selected_update import apply_update, git_blob_sha


class ModelSelectedUpdateTests(unittest.TestCase):
    def prepare(self, root):
        (root/'main.py').touch()
        (root/'proj_sec').mkdir()
        old = 'VALUE = 1\n'
        (root/'proj_sec/a.py').write_text(old)
        return {
            'proj_sec/a.py': {'updated': 'VALUE = 2\n', 'original_blob': git_blob_sha(old.encode())},
            'docs/policy.md': {'updated': 'Model-selected requirements.\n', 'original_blob': None},
        }

    def test_update_preserves_backups_and_a_second_apply_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = self.prepare(root)
            result = apply_update(root, files)
            self.assertEqual(result['changed'], 2)
            backup = Path(result['backup'])
            self.assertEqual((backup/'proj_sec/a.py').read_text(), 'VALUE = 1\n')
            self.assertEqual((root/'proj_sec/a.py').read_text(), 'VALUE = 2\n')
            self.assertTrue((root/'docs/policy.md').is_file())
            second = apply_update(root, files)
            self.assertEqual(second['changed'], 0)
            self.assertIsNone(second['backup'])

    def test_unknown_source_revision_fails_before_any_project_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = self.prepare(root)
            (root/'proj_sec/a.py').write_text('VALUE = 99\n')
            with self.assertRaisesRegex(ValueError, 'Unexpected source revision'):
                apply_update(root, files)
            self.assertEqual((root/'proj_sec/a.py').read_text(), 'VALUE = 99\n')
            self.assertFalse((root/'docs').exists())
            self.assertFalse((root/'.cache').exists())

    def test_payload_paths_cannot_escape_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            with self.assertRaisesRegex(ValueError, 'Unsafe update path'):
                apply_update(root, {'../escape.py': {'updated': 'x = 1\n', 'original_blob': None}})
            self.assertFalse((root/'.cache').exists())


if __name__ == '__main__':
    unittest.main()
