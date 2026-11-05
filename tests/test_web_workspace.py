"""Exercise the rebuilt workspace in Edge against the real compiler routes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from werkzeug.serving import make_server
import app as web

ROOT = Path(__file__).resolve().parents[1]
EDGE = Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe"


@unittest.skipUnless(EDGE.is_file() and shutil.which("g++"), "Requires Edge and g++")
class WorkspaceTests(unittest.TestCase):
    def test_example_run_tabs_and_new_file(self):
        # Keep the page loading until its real asynchronous controls have finished.
        finished = threading.Event()
        actions = """
        document.addEventListener("DOMContentLoaded", async () => {
            const el = id => document.getElementById(id);
            const wait = async check => {
                for (let i = 0; i < 800; i++) {
                    if (check()) return;
                    await new Promise(done => setTimeout(done, 50));
                }
                throw Error("Control timed out");
            };
            try {
                await wait(() => el("examples").options.length > 1);
                el("examples").value = "teste2_fatorial_fibonacci_par.minipar";
                el("examples").dispatchEvent(new Event("change"));
                await wait(() => !el("btn-run").disabled);
                if (!el("editor-minipar").value.includes("Fatorial")) throw Error("Example missing");
                el("btn-run").click();
                await wait(() => !el("btn-run").disabled);
                if (!el("terminal-output").textContent.includes("120")) throw Error(el("terminal-output").textContent);
                for (const [tab, panel, code] of [["tab-cpp","out-cpp","cpp-code"],["tab-tac","out-tac","tac-code"]]) {
                    el(tab).click();
                    if (el(panel).hidden || !el(code).textContent.includes("Fatorial")) throw Error(tab);
                }
                el("btn-clear").click();
                if (el("editor-minipar").value || el("out-exec").hidden) throw Error("New file");
                document.body.dataset.testResult = "passed";
            } catch (e) { document.body.dataset.testResult = String(e); }
            finally { await fetch("/finished"); }
        });
        """
        original = web.app.wsgi_app

        def fixture(environ, respond):
            path = environ["PATH_INFO"]
            if path in ("/hold", "/finished"):
                if path == "/hold":
                    finished.wait(50)
                else:
                    finished.set()
                respond("200 OK", [("Content-Type", "text/plain")])
                return [b""]
            if path == "/":
                with web.app.test_request_context("/"):
                    html = web.index()
                html = "\n".join(line for line in html.splitlines() if "cdnjs.cloudflare.com" not in line)
                html = html.replace("</body>", '<img src="/hold"><script>' + actions + "</script></body>")
                respond("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [html.encode()]
            return original(environ, respond)

        with tempfile.TemporaryDirectory(dir=ROOT / "output") as tmp, patch.object(web, "OUTPUT_DIR", tmp), patch("test_orchestrator.SESSION_FILE", str(Path(tmp) / "session.json")):
            server = make_server("127.0.0.1", 0, fixture, threaded=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = subprocess.run([str(EDGE), "--headless", "--disable-gpu", "--no-first-run",
                    "--disable-background-networking", "--user-data-dir=" + str(Path(tmp) / "edge"),
                    "--dump-dom", f"http://127.0.0.1:{server.server_port}/"], capture_output=True, timeout=65)
                self.assertIn(b'data-test-result="passed"', result.stdout, result.stdout[:4000])
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
