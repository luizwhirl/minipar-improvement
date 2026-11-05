"""Run with python -m unittest discover -s tests -p test_completion_monitor.py -v."""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import request
from werkzeug.serving import make_server

import app as web
import test_orchestrator as sessions

ROOT = Path(__file__).resolve().parents[1]
EDGE = Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe"


@unittest.skipUnless(EDGE.is_file() and shutil.which("g++"), "Requires Edge and g++")
class CompletionMonitorTests(unittest.TestCase):
    def check_monitor(self, delayed):
        with tempfile.TemporaryDirectory(dir=ROOT / "output") as tmp:
            work = Path(tmp)
            session_file = work / "output/.test_session.json"
            source = work / "monitor.minipar"
            source.write_text('seq { print("FIRST_MARKER");' + 'print("middle");' * 7
                              + 'print("LAST_MARKER"); }', encoding="utf-8")
            # The terminal owns and runs the program; the browser joins over HTTP.
            terminal_code = """
import sys
sys.path.insert(0, sys.argv[1])
from test_orchestrator import create_session
from menu import rodar_teste
create_session("monitor.minipar", {"multi_computer":{"count":2,"roles":["owner","viewer"]}})
input()
rodar_teste("monitor.minipar")
"""
            with subprocess.Popen([sys.executable, "-X", "utf8", "-c", terminal_code, str(ROOT)],
                                  cwd=work, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT) as terminal:
                try:
                    deadline = time.monotonic() + 10
                    while not session_file.exists() and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertTrue(session_file.exists())
                    self.observe(work, session_file, terminal, delayed)
                finally:
                    if terminal.poll() is None:
                        terminal.kill()

    def observe(self, work, session_file, terminal, delayed):
        # Exercise the real page and polling code offline. Only the unrelated CDN
        # editor and the browser's join confirmation are substituted.
        first_poll = threading.Event()
        final_poll = threading.Event()
        polls = []
        original = web.app.wsgi_app

        def fixture(environ, respond):
            path = environ["PATH_INFO"]
            if path == "/hold":
                final_poll.wait(25)
                time.sleep(1.3)  # More than two additional polling intervals.
                respond("200 OK", [("Content-Type", "text/plain")])
                return [b""]
            if path == "/":
                with web.app.test_request_context("/"):
                    html = web.index()
                import re
                html = re.sub(r'<(?:script src|link rel="stylesheet" href)="https://[^"]+"[^>]*>(?:</script>)?', '', html)
                html = html.replace('<script src="/static/js/script.js">',
                                    '<img src="/hold"><script>window.confirm=()=>true;'
                                    'window.CodeMirror={fromTextArea:()=>({})};</script>'
                                    '<script src="/static/js/script.js">')
                respond("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [html.encode()]
            monitored = path == "/api/session" and environ["QUERY_STRING"].startswith("created_at=")
            if monitored:
                first_poll.set()
                if delayed:
                    terminal.wait(timeout=25)  # Includes the active-session cleanup.
            result = original(environ, respond)
            if monitored:
                import json
                data = b"".join(result)
                result.close()
                snapshot = json.loads(data)
                polls.append(snapshot["active"])
                if not snapshot["active"]:
                    final_poll.set()
                return [data]
            return result

        with patch.object(sessions, "SESSION_FILE", str(session_file)):
            server = make_server("127.0.0.1", 0, fixture, threaded=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with subprocess.Popen([
                    str(EDGE), "--headless", "--disable-gpu", "--no-first-run",
                    "--disable-background-networking", "--disable-extensions",
                    "--user-data-dir=" + str(work / "edge"), "--dump-dom",
                    f"http://127.0.0.1:{server.server_port}/",
                ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as browser:
                    try:
                        self.assertTrue(first_poll.wait(15), "Browser did not join and poll")
                        terminal.stdin.write(b"\n")
                        terminal.stdin.flush()
                        dom, _ = browser.communicate(timeout=45)
                    finally:
                        if browser.poll() is None:
                            browser.kill()
                terminal_log = terminal.communicate(timeout=10)[0]
                self.assertEqual(terminal.returncode, 0, terminal_log)
                panel = dom.decode("utf-8").split('id="terminal-output">')[1].split("</pre>")[0]
                for text in ("100%", "FIRST_MARKER", "LAST_MARKER", "Teste concluído"):
                    self.assertIn(text, panel)
                self.assertEqual(polls.count(False), 1)
                self.assertEqual(polls[-1], False)
                self.assertEqual(True in polls, not delayed)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_normal_completion(self):
        self.check_monitor(False)

    def test_delayed_completion_after_cleanup(self):
        self.check_monitor(True)
