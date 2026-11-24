import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from proj_sec.common import external_environment
from proj_sec.model import model_python


class ModelEnvironmentTests(unittest.TestCase):
    def test_explicit_venv_python_symlink_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            launcher = Path(temporary) / "python"
            try:
                launcher.symlink_to(sys.executable)
            except OSError:
                self.skipTest("Symlinks are not permitted on this platform")
            self.assertEqual(model_python(str(launcher)), str(launcher))

    def test_frozen_environment_restores_original_library_path(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/frozen", "LD_LIBRARY_PATH_ORIG": "/original"}):
            self.assertEqual(external_environment()["LD_LIBRARY_PATH"], "/original")

    def test_model_cache_identity_distinguishes_precision(self):
        from proj_sec.model import GemmaGenerator
        with tempfile.TemporaryDirectory() as temp:
            full = GemmaGenerator(temp, dtype='float32', device='mps')
            reduced = GemmaGenerator(temp, dtype='bfloat16', device='mps')
            self.assertNotEqual(full.identity, reduced.identity)
            self.assertIn('dtypebfloat16', reduced.identity)

    def test_invalid_precision_is_rejected_before_startup(self):
        from proj_sec.model import GemmaGenerator
        with self.assertRaises(ValueError):
            GemmaGenerator('unused', dtype='invalid')

    def test_frozen_binary_finds_active_conda_python(self):
        with patch.object(sys, 'frozen', True, create=True), \
             patch.dict(os.environ, {'CONDA_PREFIX': '/conda-env'}, clear=True):
            relative = 'Scripts/python.exe' if os.name == 'nt' else 'bin/python'
            self.assertEqual(model_python(), str(Path('/conda-env') / relative))

    def test_virtualenv_takes_precedence_over_conda(self):
        with patch.object(sys, 'frozen', True, create=True), \
             patch.dict(os.environ, {'CONDA_PREFIX': '/conda-env', 'VIRTUAL_ENV': '/venv'}, clear=True):
            relative = 'Scripts/python.exe' if os.name == 'nt' else 'bin/python'
            self.assertEqual(model_python(), str(Path('/venv') / relative))
