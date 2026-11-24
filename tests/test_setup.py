import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from proj_sec.cli import main
from proj_sec.common import COLUMNS
from scripts.install_hadolint import select_asset


class InstallerTests(unittest.TestCase):
    def test_apple_silicon_requires_explicit_rosetta_option(self):
        with self.assertRaisesRegex(ValueError, '--allow-rosetta'):
            select_asset('Darwin', 'arm64')
        self.assertEqual(select_asset('Darwin', 'arm64', True), 'Darwin-x86_64')

    def test_native_platform_assets(self):
        self.assertEqual(select_asset('Linux', 'x86_64'), 'Linux-x86_64')
        self.assertEqual(select_asset('Linux', 'aarch64'), 'Linux-arm64')
        self.assertEqual(select_asset('Windows', 'AMD64'), 'Windows-x86_64.exe')

    def test_unsupported_platform_is_rejected(self):
        with self.assertRaises(ValueError):
            select_asset('UnknownOS', 'unknown')


class PipelineMemoryTests(unittest.TestCase):
    def test_model_is_closed_before_scanning_and_errors_propagate(self):
        class Generator:
            active = False
            identity = 'unit-test-double'
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                Generator.active = True
                return self
            def __exit__(self, *args):
                Generator.active = False
        def scan(*args, **kwargs):
            self.assertFalse(Generator.active)
            frame = pd.DataFrame(columns=COLUMNS)
            frame.attrs['scan_status'] = 'completed-with-tool-errors'
            return frame
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'out'
            with patch('proj_sec.cli.GemmaGenerator', Generator), \
                 patch('proj_sec.cli._prepare', return_value=(('left', 'right'), [])), \
                 patch('proj_sec.cli.extract_kdes', return_value={'zero-shot': ('left.yaml', 'right.yaml')}) as extract, \
                 patch('proj_sec.cli._compare', return_value=('names.txt', 'requirements.txt', 'rules.txt')), \
                 patch('proj_sec.cli.run_hadolint', side_effect=scan):
                result = main(['run', 'left.pdf', 'right.pdf', '--dockerfiles', 'data.zip', '--output', str(output)])
            self.assertEqual(result, 0)
            self.assertEqual(extract.call_args.kwargs['cache_dir'], Path('.cache/gemma'))
            status = json.loads((output / 'run-status.json').read_text())
            self.assertEqual(status['status'], 'completed-with-scan-errors')
