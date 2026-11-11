"""A terminal monitor must follow its session and keep progress output bounded."""
from contextlib import redirect_stdout
import copy
import io
import os
import unittest
from unittest.mock import patch

import test_orchestrator as sessions


class TerminalMonitorTests(unittest.TestCase):
    def state(self, identity="original", status="running", **extra):
        return {"created_at": identity, "status": status,
                "test_file": identity + ".minipar", "titulo": identity,
                "participants": [], "required_participants": 2,
                "phase": "executing", "phase_message": "Executando " + identity,
                "progress_percent": 90, "progress_log": [], **extra}

    def test_completion_remains_available_after_the_active_session_is_replaced(self):
        original = self.state()
        newer = self.state("newer")
        archived = self.state(status="completed", phase="done", progress_percent=100,
                              execution_output="ORIGINAL_RESULT")
        output = io.StringIO()
        with patch.object(sessions, "_load_session", return_value=newer), \
                patch.object(sessions, "load_completed_session", return_value=archived) as load, \
                patch.object(sessions, "append_session_log") as append, redirect_stdout(output):
            self.assertTrue(sessions.run_joiner_progress_monitor(original))
        load.assert_called_once_with("original")
        append.assert_not_called()
        self.assertIn("ORIGINAL_RESULT", output.getvalue())
        self.assertNotIn("Executando newer", output.getvalue())

    def test_replaced_session_without_completion_does_not_follow_another_execution(self):
        with patch.object(sessions, "_load_session", return_value=self.state("other")), \
                patch.object(sessions, "load_completed_session", return_value=None), \
                patch.object(sessions, "append_session_log") as append, redirect_stdout(io.StringIO()):
            self.assertTrue(sessions.run_joiner_progress_monitor(self.state()))
        append.assert_not_called()

    def test_repeated_polls_do_not_flood_captured_output(self):
        state = self.state()
        done = self.state(status="cancelled", phase="cancelled", phase_message="Sessão encerrada.")
        snapshots = [copy.deepcopy(state) for _ in range(8)] + [done]
        output = io.StringIO()
        with patch.object(sessions, "_load_session", side_effect=snapshots), \
                patch.object(sessions, "append_session_log"), \
                patch.object(sessions.time, "sleep"), redirect_stdout(output):
            self.assertFalse(sessions.run_joiner_progress_monitor(state))
        self.assertEqual(output.getvalue().count("Progresso: 90%"), 2)
        self.assertNotIn("\r", output.getvalue())

    def test_spinner_fits_a_narrow_terminal(self):
        class Terminal(io.StringIO):
            def isatty(self):
                return True

        state = self.state()
        done = self.state(status="cancelled", phase="cancelled")
        output = Terminal()
        with patch.object(sessions, "_load_session", side_effect=[state, state, done]), \
                patch.object(sessions, "append_session_log"), \
                patch.object(sessions.time, "sleep"), \
                patch.object(sessions.shutil, "get_terminal_size", return_value=os.terminal_size((45, 20))), \
                redirect_stdout(output):
            self.assertFalse(sessions.run_joiner_progress_monitor(state))
        frames = output.getvalue().split("\r")[1:]
        self.assertTrue(frames)
        for frame in frames:
            self.assertLessEqual(len(frame.split("\n", 1)[0]), 44)
