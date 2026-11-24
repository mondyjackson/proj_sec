import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.package_coverage_results import PAIRS, STYLES, package_results


class CoveragePackageTests(unittest.TestCase):
    def prepare(self, source):
        for pair in PAIRS:
            directory = source / pair; directory.mkdir(parents=True)
            (directory / 'run-status.json').write_text(json.dumps({'command': 'run', 'status': 'completed-with-scan-errors'}))
            (directory / 'coverage-review.json').write_text(json.dumps({'status': 'completed-needs-quality-review'}))
            for style in STYLES:
                scan = directory / style; scan.mkdir()
                for name in ('element-names.txt', 'element-requirements.txt', 'hadolint-rules.txt', 'scan-manifest.json', 'scan-status.json'):
                    (scan / name).write_text('{}')
                for side in ('left', 'right'):
                    (scan / (side + '-test-kdes.yaml')).write_text('element1: {}\n')
                (scan / 'results.csv').write_text('FilePath,DefaultSeverity,RULEID,COUNT\na,warning,DL3002,1\n')
                (scan / 'hadolint-findings.jsonl').write_text('Large per-file evidence is deliberately outside the compact bundle.')

    def test_manifest_preserves_all_paths_even_when_csv_contents_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'runs'; self.prepare(source)
            different = source / PAIRS[0] / STYLES[0] / 'results.csv'
            different.write_text(different.read_text().replace(',1\n', ',2\n'))
            target = root / 'review.zip'; manifest = package_results(source, target)
            self.assertEqual(manifest['original_csv_paths'], 15)
            self.assertEqual(manifest['unique_csv_files'], 2)
            with zipfile.ZipFile(target) as archive:
                for relative, info in manifest['csv_paths'].items():
                    self.assertEqual(archive.read(info['archive_member']), (source / relative).read_bytes())
                self.assertFalse(any(name.endswith('hadolint-findings.jsonl') for name in archive.namelist()))
                stored = json.loads(archive.read('csv-manifest.json'))
                self.assertEqual(stored, manifest)
                self.assertEqual(stored['statuses'][PAIRS[0]]['run'], 'completed-with-scan-errors')

    def test_an_incomplete_pair_cannot_create_a_completed_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'runs'; self.prepare(source)
            (source / PAIRS[-1] / 'run-status.json').write_text('{"command":"run","status":"incomplete"}')
            target = root / 'review.zip'
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                package_results(source, target)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
