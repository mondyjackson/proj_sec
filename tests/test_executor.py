import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from proj_sec.common import COLUMNS, NO_DIFFERENCES, NO_MAPPING, NO_NAMES, NO_REQUIREMENTS
from proj_sec.executor import export_csv, load_difference_reports, map_hadolint_rules, run_hadolint


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.names = self.root / "names.txt"; self.names.write_text(NO_NAMES + "\n")
        self.requirements = self.root / "requirements.txt"; self.requirements.write_text(NO_REQUIREMENTS + "\n")
        self.mapping = self.root / "rules.txt"; self.mapping.write_text(NO_DIFFERENCES + "\n")
        self.fake_bin = self.root / "hadolint"
        self.fake_bin.write_text("mock executable")
        self.fake_bin.chmod(0o755)
        self.archive = self.root / "dockerfiles.zip"
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("nested/Dockerfile", "FROM ubuntu:latest\nUSER root\nADD hello.txt /hello.txt\n")

    def test_load_difference_reports(self):
        self.assertEqual(load_difference_reports(self.names, self.requirements), (NO_NAMES, NO_REQUIREMENTS))
        self.requirements.write_text("malformed one-field row")
        with self.assertRaises(ValueError):
            load_difference_reports(self.names, self.requirements)

    def test_map_hadolint_rules(self):
        reports = (NO_NAMES, 'Ensure that COPY is used instead of ADD in Dockerfiles,Use COPY.\n')
        self.assertEqual(map_hadolint_rules(reports, self.mapping).read_text().strip(), "DL3020")

    def test_run_hadolint(self):
        findings = [{"code": "DL3002", "level": "warning", "message": "Root user", "line": 2}] * 2
        version = subprocess.CompletedProcess([], 0, "Haskell Dockerfile Linter 2.12.0\n", "")
        def invoke(command, **kwargs):
            if "--version" in command:
                return version
            return subprocess.CompletedProcess([], 0, json.dumps([{**f, "file": command[-1]} for f in findings]), "")
        with patch("proj_sec.executor.subprocess.run", side_effect=invoke) as runner:
            frame = run_hadolint(self.mapping, self.archive, hadolint=str(self.fake_bin))
        self.assertEqual(frame.to_dict("records"), [{"FilePath": "nested/Dockerfile", "DefaultSeverity": "warning", "RULEID": "DL3002", "COUNT": 2}])
        self.assertIn("--no-fail", runner.call_args.args[0])

    def test_export_csv(self):
        frame = pd.DataFrame([["Dockerfile", "warning", "DL3002", 2]], columns=COLUMNS)
        output = export_csv(frame, self.root / "results.csv")
        self.assertEqual(output.read_text(), "FilePath,DefaultSeverity,RULEID,COUNT\nDockerfile,warning,DL3002,2\n")

    def test_no_differences_and_no_mapping_are_distinct(self):
        self.assertEqual(map_hadolint_rules((NO_NAMES, NO_REQUIREMENTS), self.mapping).read_text().strip(), NO_DIFFERENCES)
        self.assertEqual(map_hadolint_rules(("Configure host auditing", NO_REQUIREMENTS), self.mapping).read_text().strip(), NO_MAPPING)

    def test_traversal_zip_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("../../Dockerfile", "FROM ubuntu\n")
        version = subprocess.CompletedProcess([], 0, "Hadolint 2.12.0", "")
        with patch("proj_sec.executor.subprocess.run", return_value=version):
            with self.assertRaisesRegex(ValueError, "Unsafe ZIP path"):
                run_hadolint(self.mapping, self.archive, hadolint=str(self.fake_bin))

    def test_scan_failure_is_not_an_empty_success(self):
        version = subprocess.CompletedProcess([], 0, "Hadolint 2.12.0", "")
        failed = subprocess.CompletedProcess([], 2, "", "tool failure")
        with patch("proj_sec.executor.subprocess.run", side_effect=[version, failed]):
            with self.assertRaisesRegex(RuntimeError, "tool failure"):
                run_hadolint(self.mapping, self.archive, hadolint=str(self.fake_bin))

    def test_empty_scan_csv_retains_headers(self):
        self.assertEqual(export_csv(pd.DataFrame(columns=COLUMNS), self.root / "empty.csv").read_text(), ",".join(COLUMNS) + "\n")

    def test_runtime_crash_is_isolated_and_recorded(self):
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("crash/Dockerfile", "FROM alpine\n# CRASH\n")
        calls = []
        def invoke(command, **kwargs):
            if "--version" in command:
                return subprocess.CompletedProcess([], 0, "Hadolint 2.12.0", "")
            paths = command[7:]
            calls.append(len(paths))
            if any("CRASH" in Path(path).read_text() for path in paths):
                return subprocess.CompletedProcess([], 1, "", "hadolint: index too large\nCallStack: runtime failure")
            return subprocess.CompletedProcess([], 0, json.dumps([
                {"file": path, "code": "DL3002", "level": "warning", "message": "Root", "line": 2} for path in paths
            ]), "")
        evidence = self.root / "evidence"
        with patch("proj_sec.executor.subprocess.run", side_effect=invoke):
            frame = run_hadolint(self.mapping, self.archive, hadolint=str(self.fake_bin), evidence_dir=evidence)
        self.assertEqual(calls, [2, 1, 1])
        self.assertEqual(set(frame.FilePath), {"nested/Dockerfile"})
        manifest = json.loads((evidence / "scan-manifest.json").read_text())
        self.assertEqual(manifest["candidate_files"], 2)
        self.assertEqual(manifest["tool_error_files"], 1)
        self.assertEqual(manifest["status"], "completed-with-tool-errors")
        self.assertIn("CallStack", (evidence / "hadolint-findings.jsonl").read_text())

    def test_interrupted_scan_resumes_completed_content(self):
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("second/Dockerfile", "FROM alpine:3.20\n")
        fail = True
        def invoke(command, **kwargs):
            if "--version" in command:
                return subprocess.CompletedProcess([], 0, "Hadolint 2.12.0", "")
            if fail and "alpine" in Path(command[-1]).read_text():
                return subprocess.CompletedProcess([], 2, "", "tool failure")
            return subprocess.CompletedProcess([], 0, "[]", "")
        evidence = self.root / "evidence"
        with patch("proj_sec.executor.subprocess.run", side_effect=invoke):
            with self.assertRaisesRegex(RuntimeError, "tool failure"):
                run_hadolint(self.mapping, self.archive, hadolint=str(self.fake_bin), evidence_dir=evidence, batch_size=1, workers=1)
            self.assertEqual(json.loads((evidence / "scan-status.json").read_text())["status"], "incomplete")
            fail = False
            run_hadolint(self.mapping, self.archive, hadolint=str(self.fake_bin), evidence_dir=evidence, batch_size=1, workers=1)
        manifest = json.loads((evidence / "scan-manifest.json").read_text())
        self.assertEqual(manifest["unique_cache_hits"], 1)
        self.assertEqual(manifest["unique_executed"], 1)


@unittest.skipUnless(shutil.which(os.environ.get("HADOLINT_BIN", "hadolint")), "Real Hadolint is not installed")
class HadolintIntegrationTests(unittest.TestCase):
    setUp = ExecutorTests.setUp
    def test_real_full_and_selected_scans(self):
        binary = os.environ.get("HADOLINT_BIN", "hadolint")
        full = run_hadolint(self.mapping, self.archive, hadolint=binary)
        self.assertTrue({"DL3002", "DL3020", "DL3057"}.issubset(set(full["RULEID"])))
        self.mapping.write_text("DL3020\n")
        selected = run_hadolint(self.mapping, self.archive, hadolint=binary)
        self.assertEqual(set(selected["RULEID"]), {"DL3020"})

    def test_real_no_mapping_runs_all_rules(self):
        self.mapping.write_text(NO_MAPPING + "\n")
        frame = run_hadolint(self.mapping, self.archive, hadolint=os.environ.get("HADOLINT_BIN", "hadolint"))
        self.assertIn("DL3002", set(frame["RULEID"]))

    def test_duplicate_files_cache_and_original_paths(self):
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("other/Dockerfile", "FROM ubuntu:latest\nUSER root\nADD hello.txt /hello.txt\n")
        binary = os.environ.get("HADOLINT_BIN", "hadolint")
        evidence = self.root / "evidence"
        first = run_hadolint(self.mapping, self.archive, hadolint=binary, evidence_dir=evidence, batch_size=1)
        manifest = json.loads((evidence / "scan-manifest.json").read_text())
        self.assertEqual(manifest["unique_executed"], 1)
        self.assertEqual(manifest["duplicate_files_reused"], 1)
        self.assertEqual(set(first.FilePath), {"nested/Dockerfile", "other/Dockerfile"})
        again = run_hadolint(self.mapping, self.archive, hadolint=binary, evidence_dir=evidence)
        pd.testing.assert_frame_equal(first, again)
        manifest = json.loads((evidence / "scan-manifest.json").read_text())
        self.assertEqual(manifest["unique_executed"], 0)
        self.assertEqual(manifest["unique_cache_hits"], 1)
        self.mapping.write_text("DL3020\n")
        selected = run_hadolint(self.mapping, self.archive, hadolint=binary, evidence_dir=evidence)
        self.assertEqual(set(selected.RULEID), {"DL3020"})
        self.assertEqual(json.loads((evidence / "scan-manifest.json").read_text())["unique_executed"], 1)

    def test_malformed_and_non_utf8_inputs_are_recorded(self):
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("broken/Dockerfile", "NOT_AN_INSTRUCTION invalid\n")
            archive.writestr("nonutf8/Dockerfile", b"FROM alpine\n# \xff\n")
        binary = os.environ.get("HADOLINT_BIN", "hadolint")
        evidence = self.root / "evidence"
        results = run_hadolint(self.mapping, self.archive, hadolint=binary, evidence_dir=evidence)
        manifest = json.loads((evidence / "scan-manifest.json").read_text())
        self.assertEqual(manifest["status"], "completed-with-input-errors")
        self.assertEqual(manifest["candidate_files"], 3)
        self.assertEqual(manifest["parse_error_files"], 1)
        self.assertEqual(manifest["encoding_error_files"], 1)
        self.assertIn("DL1000", set(results.RULEID))
        self.mapping.write_text("DL3020\n")
        selected = run_hadolint(self.mapping, self.archive, hadolint=binary, evidence_dir=evidence)
        self.assertEqual(set(selected.RULEID), {"DL3020"})
        self.assertEqual(json.loads((evidence / "scan-manifest.json").read_text())["parse_error_files"], 1)

    def test_batched_results_equal_individual_results(self):
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("clean/Dockerfile", "FROM alpine:3.20\nUSER app\nHEALTHCHECK NONE\n")
            archive.writestr("third/Dockerfile", "FROM python\nRUN pip install requests\n")
        binary = os.environ.get("HADOLINT_BIN", "hadolint")
        one = run_hadolint(self.mapping, self.archive, hadolint=binary, workers=1, batch_size=1)
        many = run_hadolint(self.mapping, self.archive, hadolint=binary, workers=2, batch_size=2)
        pd.testing.assert_frame_equal(one, many)


class LargeArchiveTests(unittest.TestCase):
    def test_archive_above_old_20000_entry_limit(self):
        from proj_sec.executor import _members
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for i in range(20_001):
                    archive.writestr(f"__MACOSX/._{i}", b"")
                archive.writestr("Dockerfile", "FROM alpine:3.20\n")
            with zipfile.ZipFile(path) as archive:
                self.assertEqual([i.filename for i in _members(archive)], ["Dockerfile"])


if __name__ == "__main__":
    unittest.main()
