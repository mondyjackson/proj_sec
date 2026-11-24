import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.restore_final_results import PAIRS, STYLES, archive_from_parts, restore


def bundle():
    data = b'FilePath,DefaultSeverity,RULEID,COUNT\na,warning,DL3002,1\n'
    sha = hashlib.sha256(data).hexdigest()
    member = f'shared-csv/{sha}.csv'
    manifest = {'format': 'proj-sec-reviewed-results-v1', 'csv_paths': {
        f'{pair}/{style}/results.csv': {'sha256': sha, 'bytes': len(data), 'archive_member': member}
        for pair in PAIRS for style in STYLES}}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, data)
        archive.writestr('coverage-final/v0-v1/run-status.json', '{"status":"completed"}')
        archive.writestr('csv-manifest.json', json.dumps(manifest))
    return stream.getvalue(), data


class ResultRestoreTests(unittest.TestCase):
    def test_shared_csv_is_restored_to_all_paths_and_matching_files_are_preserved(self):
        content, data = bundle()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'results'
            restore(io.BytesIO(content), output)
            for pair in PAIRS:
                for style in STYLES:
                    self.assertEqual((output / pair / style / 'results.csv').read_bytes(), data)
            path = output / PAIRS[0] / STYLES[0] / 'results.csv'
            before = path.stat().st_mtime_ns
            restore(io.BytesIO(content), output)
            self.assertEqual(path.stat().st_mtime_ns, before)

    def test_existing_conflict_is_detected_before_any_new_file_is_written(self):
        content, _ = bundle()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'results'
            path = output / PAIRS[-1] / STYLES[-1] / 'results.csv'
            path.parent.mkdir(parents=True)
            path.write_text('preserve this different file')
            with self.assertRaisesRegex(ValueError, 'Existing file differs'):
                restore(io.BytesIO(content), output)
            self.assertEqual(path.read_text(), 'preserve this different file')
            self.assertFalse((output / 'v0-v1/run-status.json').exists())

    def test_corrupted_archive_part_is_rejected_before_restoration(self):
        content, _ = bundle()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            part = source / 'results.part001'
            part.write_bytes(content)
            manifest = {'archive_bytes': len(content), 'archive_sha256': hashlib.sha256(content).hexdigest(),
                        'parts': [{'name': part.name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}]}
            (source / 'manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(archive_from_parts(source).read(), content)
            part.write_bytes(content[:-1] + bytes([content[-1] ^ 1]))
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                archive_from_parts(source)


if __name__ == '__main__':
    unittest.main()
