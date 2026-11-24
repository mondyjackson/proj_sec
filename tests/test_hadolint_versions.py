import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from proj_sec.common import NO_DIFFERENCES
from proj_sec.executor import _hadolint_catalog, run_hadolint
from scripts import run_all_pairs


class HadolintVersionTests(unittest.TestCase):
    def test_version_catalogs_include_additions_and_removal(self):
        old = _hadolint_catalog('Haskell Dockerfile Linter 2.12.0\n')
        new = _hadolint_catalog('Haskell Dockerfile Linter 2.15.1\n')
        self.assertEqual(old['DL3005'], 'error')
        self.assertNotIn('DL3005', new)
        self.assertNotIn('DL3066', old)
        self.assertEqual(new['DL3066'], 'info')
        self.assertEqual(new['DL3067'], 'warning')
        self.assertEqual(new['DL3057'], 'ignore')
        self.assertEqual(new['DL3020'], 'error')

    def test_unknown_and_prerelease_versions_are_rejected(self):
        for version in ('2.15.0', '2.15.10', '12.15.1', '2.15.1-beta', '2.15.1+dev', 'unknown'):
            with self.subTest(version=version):
                with self.assertRaisesRegex(ValueError, 'Supported Hadolint versions'):
                    _hadolint_catalog('Haskell Dockerfile Linter ' + version)

    def test_removed_rule_is_rejected_before_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping = Path(tmp) / 'rules.txt'
            mapping.write_text('DL3005\n')
            version = subprocess.CompletedProcess([], 0, 'Hadolint 2.15.1', '')
            with patch('proj_sec.executor.shutil.which', return_value='/fake/hadolint'), \
                 patch('proj_sec.executor.subprocess.run', return_value=version), \
                 patch('proj_sec.scan_engine.scan_archive') as scanner:
                with self.assertRaisesRegex(ValueError, 'catalog for this Hadolint version'):
                    run_hadolint(mapping, Path(tmp) / 'not-opened.zip')
                scanner.assert_not_called()

    def test_runner_prefers_installed_scanner(self):
        with patch('scripts.run_all_pairs.shutil.which', return_value='/opt/homebrew/bin/hadolint'):
            self.assertEqual(run_all_pairs._default_hadolint(), '/opt/homebrew/bin/hadolint')

    def test_runner_falls_back_to_local_scanner(self):
        with patch('scripts.run_all_pairs.shutil.which', return_value=None):
            fallback = Path(run_all_pairs._default_hadolint())
            self.assertEqual(fallback.parent, Path(run_all_pairs.__file__).resolve().parents[1] / 'tools')
            self.assertEqual(fallback.name, 'hadolint.exe' if os.name == 'nt' else 'hadolint')

    def test_runner_respects_explicit_scanner_path(self):
        with patch('sys.argv', ['run_all_pairs.py', '--mode', 'run', '--hadolint', '/custom/hadolint']), \
             patch('scripts.run_all_pairs.subprocess.run') as invoke:
            run_all_pairs.main()
        self.assertEqual(invoke.call_count, 5)
        for call in invoke.call_args_list:
            command = call.args[0]
            self.assertEqual(command[command.index('--hadolint') + 1], '/custom/hadolint')


@unittest.skipUnless(shutil.which(os.environ.get('HADOLINT_BIN', 'hadolint')), 'Real Hadolint is not installed')
class HadolintVersionIntegrationTests(unittest.TestCase):
    def test_full_scan_uses_matching_defaults_and_selected_scan_excludes_new_rules(self):
        binary = os.environ.get('HADOLINT_BIN', 'hadolint')
        version = subprocess.run([binary, '--version'], capture_output=True, text=True, check=True).stdout
        catalog = _hadolint_catalog(version)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / 'rules.txt'
            mapping.write_text(NO_DIFFERENCES + '\n')
            archive = root / 'dockerfiles.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('Dockerfile', 'FROM ubuntu:latest\nUSER root\nADD hello.txt /hello.txt\n')
            frame = run_hadolint(mapping, archive, hadolint=binary, evidence_dir=root / 'full')
            self.assertEqual('DL3066' in set(frame.RULEID), 'DL3066' in catalog)
            if 'DL3066' in catalog:
                self.assertEqual(set(frame.loc[frame.RULEID == 'DL3066', 'DefaultSeverity']), {'info'})
            self.assertEqual(set(frame.loc[frame.RULEID == 'DL3057', 'DefaultSeverity']), {'ignore'})
            manifest = json.loads((root / 'full/scan-manifest.json').read_text())
            self.assertEqual(manifest['version'], version.strip())
            mapping.write_text('DL3020\n')
            selected = run_hadolint(mapping, archive, hadolint=binary)
            self.assertEqual(set(selected.RULEID), {'DL3020'})


if __name__ == '__main__':
    unittest.main()
