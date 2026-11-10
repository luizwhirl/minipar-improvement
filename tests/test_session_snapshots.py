"""Atomic session publication tolerates brief Windows reader locks."""
import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_orchestrator as sessions


ROOT = Path(__file__).resolve().parents[1]


class SessionSnapshotTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "output").mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="snapshot-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.target = self.work / "session.json"
        self.before = {"generation": "previous", "status": "waiting"}
        self.after = {"generation": "current", "status": "running", "execution_output": "Olá, MiniPar!"}
        self.target.write_text(json.dumps(self.before), encoding="utf-8")

    def assert_only_published_file_remains(self):
        self.assertEqual(list(self.work.iterdir()), [self.target], "The temporary snapshot was not removed")

    def test_transient_windows_sharing_errors_preserve_atomicity_then_publish(self):
        real_replace = os.replace
        for winerror in (5, 32, 33):
            with self.subTest(winerror=winerror):
                self.target.write_text(json.dumps(self.before), encoding="utf-8")
                error = PermissionError(errno.EACCES, "Reader temporarily holds the session")
                error.winerror = winerror
                calls = []

                def replace_after_unlock(source, destination):
                    calls.append((source, destination))
                    # A reader sees the complete old snapshot until the atomic
                    # replacement succeeds. The pending snapshot is complete too.
                    self.assertEqual(json.loads(self.target.read_text(encoding="utf-8")), self.before)
                    self.assertEqual(json.loads(Path(source).read_text(encoding="utf-8")), self.after)
                    if len(calls) == 1:
                        raise error
                    return real_replace(source, destination)

                with patch.object(sessions.os, "replace", side_effect=replace_after_unlock) as replace, \
                        patch.object(sessions.time, "sleep") as sleep:
                    sessions._write_snapshot(str(self.target), self.after)
                self.assertEqual(replace.call_count, 2)
                sleep.assert_called_once()
                self.assertEqual(json.loads(self.target.read_text(encoding="utf-8")), self.after)
                self.assert_only_published_file_remains()

    def test_persistent_windows_permission_error_is_bounded_and_propagates(self):
        error = PermissionError(errno.EACCES, "The session remains locked")
        error.winerror = 5
        calls = []

        def always_locked(source, destination):
            calls.append((source, destination))
            if len(calls) > 20:
                self.fail("Snapshot replacement did not stop retrying a persistent error")
            raise error

        with patch.object(sessions.os, "replace", side_effect=always_locked) as replace, \
                patch.object(sessions.time, "sleep") as sleep:
            with self.assertRaises(PermissionError) as raised:
                sessions._write_snapshot(str(self.target), self.after)
        self.assertIs(raised.exception, error)
        self.assertGreater(replace.call_count, 1)
        self.assertLessEqual(replace.call_count, 20)
        self.assertTrue(sleep.called)
        self.assertEqual(json.loads(self.target.read_text(encoding="utf-8")), self.before)
        self.assert_only_published_file_remains()

    def test_nonsharing_errors_are_not_retried_and_leave_the_previous_snapshot(self):
        errors = [FileNotFoundError(errno.ENOENT, "The destination disappeared"),
                  PermissionError(errno.EACCES, "A permission failure without a Windows sharing code")]
        errors[0].winerror = 2
        for error in errors:
            with self.subTest(error=error):
                with patch.object(sessions.os, "replace", side_effect=error) as replace, \
                        patch.object(sessions.time, "sleep") as sleep:
                    with self.assertRaises(type(error)) as raised:
                        sessions._write_snapshot(str(self.target), self.after)
                self.assertIs(raised.exception, error)
                replace.assert_called_once()
                sleep.assert_not_called()
                self.assertEqual(json.loads(self.target.read_text(encoding="utf-8")), self.before)
                self.assert_only_published_file_remains()


if __name__ == "__main__":
    unittest.main()
