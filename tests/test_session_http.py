"""Regression checks for HTTP session requests and terminal participation prompts."""
import copy
import unittest
from unittest.mock import patch

import app as web
import test_orchestrator as sessions


class SessionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = web.app.test_client()
        self.session = {
            "status": "waiting",
            "participants": [{"terminal_id": "initiator", "role": "server"}],
            "required_participants": 2,
            "roles": ["server", "client"],
        }
        self.state = patch.object(sessions, "_load_session", return_value=self.session)
        self.state.start()
        self.addCleanup(self.state.stop)
        identity = patch.object(sessions, "get_terminal_id", return_value="browser")
        identity.start()
        self.addCleanup(identity.stop)

    def test_polling_never_prompts_or_mutates_session(self):
        for status in ("waiting", "ready", "running", "completed", "cancelled"):
            with self.subTest(status=status):
                self.session["status"] = status
                before = copy.deepcopy(self.session)
                with patch("builtins.input", side_effect=AssertionError("HTTP prompted")):
                    for _ in range(3):
                        response = self.client.get("/api/session")
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json["needs_choice"], status in ("waiting", "ready", "running"))
                self.assertEqual(self.session, before)

    def test_explicit_browser_join_never_prompts(self):
        for status in ("waiting", "ready", "running"):
            with self.subTest(status=status):
                self.session["status"] = status
                self.session["participants"] = [{"terminal_id": "initiator", "role": "server"}]
                with patch("builtins.input", side_effect=AssertionError("HTTP prompted")), patch.object(sessions, "_save_session"), patch.object(sessions, "append_session_log"):
                    response = self.client.post("/api/session/join")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["session"]["participants"][-1]["terminal_id"], "browser")

    def test_inactive_or_missing_session_cannot_be_joined(self):
        for session in (None, {"status": "completed"}, {"status": "cancelled"}):
            with self.subTest(session=session), patch.object(sessions, "_load_session", return_value=session), patch("builtins.input", side_effect=AssertionError("HTTP prompted")):
                self.assertEqual(self.client.post("/api/session/join").status_code, 404)
                self.assertFalse(self.client.get("/api/session").json["active"])

    def test_terminal_still_prompts_and_returns_choice(self):
        for answer, expected in (("1", "independent"), ("2", "join")):
            with self.subTest(answer=answer), patch("builtins.input", return_value=answer) as prompt, patch("builtins.print"):
                action, session = sessions.check_active_session_for_new_terminal()
                self.assertEqual(action, expected)
                self.assertIs(session, self.session)
                prompt.assert_called_once()

    def test_existing_waiting_participant_does_not_need_choice(self):
        self.session["participants"].append({"terminal_id": "browser", "role": "client"})
        with patch("builtins.input", side_effect=AssertionError("Unexpected prompt")):
            self.assertFalse(self.client.get("/api/session").json["needs_choice"])
            self.assertIsNone(sessions.check_active_session_for_new_terminal()[0])


if __name__ == "__main__":
    unittest.main()
