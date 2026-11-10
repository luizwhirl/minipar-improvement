"""Check build/download controls, current editor input, and streamed output in Edge."""
import html
import io
import json
from contextlib import nullcontext
import os
from pathlib import Path
import re
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


@unittest.skipUnless(EDGE.is_file(), "Requires Microsoft Edge")
class ExecutionWorkspaceTests(unittest.TestCase):
    def exercise_browser(self, actions, *, deterministic_stream=False, custom_examples=None):
        finished = threading.Event()
        stream_observed = threading.Event()
        requests = []
        original = web.app.wsgi_app
        harness = r"""
        document.addEventListener("DOMContentLoaded", async () => {
            const el = id => document.getElementById(id);
            const assert = (condition, message) => { if (!condition) throw Error(message); };
            const wait = async (check, message) => {
                for (let attempt = 0; attempt < 700; attempt++) {
                    if (check()) return;
                    await new Promise(done => setTimeout(done, 50));
                }
                throw Error(message || "Execution controls timed out");
            };
            const setSource = code => {
                el("editor-minipar").value = code;
                el("editor-minipar").dispatchEvent(new Event("input", { bubbles: true }));
            };
            const terminal = () => el("terminal-output").textContent.replaceAll("\r\n", "\n");
            window.prompt = window.alert = window.confirm = () => {
                throw Error("Execution unexpectedly used a modal prompt or stale example metadata");
            };
            // Keep the genuine build/link flow, but avoid downloading an executable
            // into the user's browser download directory during a UI regression test.
            document.addEventListener("click", event => {
                if (event.target.closest?.("#executable-link")) event.preventDefault();
            }, true);
            try {
                await wait(() => el("examples").options.length > 1, "Examples did not load");
                __ACTIONS__
                document.body.dataset.testResult = "passed";
            } catch (error) {
                document.body.dataset.testResult = "failed";
                document.body.dataset.testError = error.stack || String(error);
            } finally { await fetch("/finished"); }
        });
        """.replace("__ACTIONS__", actions)

        def encode(event, newline=True):
            return (json.dumps(event, ensure_ascii=False) + ("\n" if newline else "")).encode("utf-8")

        def stream_fixture():
            yield encode({"type": "phase", "phase": "executing", "message": "Executando teste de fluxo."})
            first = encode({"type": "output", "stream": "stdout", "text": "PRIMEIRO ÇÃO sem nova linha"})
            # Exercise decoding with a multibyte character divided between yields.
            cut = first.index("Ç".encode("utf-8")) + 1
            yield first[:cut]
            yield first[cut:]
            if not stream_observed.wait(20):
                yield encode({"type": "complete", "success": False, "exit_code": None,
                              "stdout": "", "stderr": "Browser did not observe output before completion",
                              "cpp": "", "tac": "", "download_url": None, "filename": "stream.exe"})
                return
            yield encode({"type": "output", "stream": "stdout", "text": " FINAL\n"})
            # A complete final event without a trailing newline must still be read.
            yield encode({"type": "complete", "success": True, "exit_code": 0,
                          "stdout": "PRIMEIRO ÇÃO sem nova linha FINAL\n", "stderr": "",
                          "cpp": "", "tac": "", "download_url": None, "filename": "stream.exe"}, newline=False)

        def fixture(environ, respond):
            path = environ["PATH_INFO"]
            if path in ("/hold", "/finished", "/stream-observed"):
                if path == "/hold":
                    finished.wait(80)
                elif path == "/stream-observed":
                    stream_observed.set()
                else:
                    finished.set()
                respond("200 OK", [("Content-Type", "text/plain")])
                return [b""]
            if path in ("/api/build", "/api/execute", "/api/compile", "/api/session/create", "/api/analyze"):
                raw = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or 0))
                environ["wsgi.input"] = io.BytesIO(raw)
                requests.append((path, json.loads(raw) if raw else {}))
            if path == "/api/execute" and deterministic_stream:
                respond("200 OK", [("Content-Type", "application/x-ndjson; charset=utf-8"),
                                   ("Cache-Control", "no-store")])
                return stream_fixture()
            if path == "/":
                with web.app.test_request_context("/"):
                    page = web.index()
                # Only the external editor CDN is removed. The production local
                # execution parser and UI remain intact, as do real API routes.
                page = "\n".join(line for line in page.splitlines() if "cdnjs.cloudflare.com" not in line)
                page = page.replace("</body>", '<img src="/hold" alt=""><script>' + harness + "</script></body>")
                respond("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [page.encode("utf-8")]
            return original(environ, respond)

        (ROOT / "output").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="execution-workspace-") as tmp:
            work = Path(tmp)
            if custom_examples:
                examples = work / "examples"
                examples.mkdir()
                for filename, code in custom_examples.items():
                    (examples / filename).write_text(code, encoding="utf-8")
            with patch.object(web, "OUTPUT_DIR", str(work / "compiler-output")), \
                    patch("test_orchestrator.SESSION_FILE", str(work / "session.json")), \
                    (patch.object(web, "TESTS_DIR", str(examples)) if custom_examples else nullcontext()):
                server = make_server("127.0.0.1", 0, fixture, threaded=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    browser = subprocess.run([
                        str(EDGE), "--headless", "--disable-gpu", "--no-first-run",
                        "--disable-background-networking", "--disable-extensions",
                        "--user-data-dir=" + str(work / "edge"), "--dump-dom",
                        f"http://127.0.0.1:{server.server_port}/",
                    ], capture_output=True, timeout=90)
                    dom = browser.stdout.decode("utf-8", errors="replace")
                    failure = re.search(r'data-test-error="([^"]*)"', dom)
                    detail = html.unescape(failure.group(1)) if failure else (
                        f"Edge exit code: {browser.returncode}\n"
                        + browser.stderr.decode("utf-8", errors="replace")[-3000:] + dom[-4000:])
                    self.assertIn('data-test-result="passed"', dom, detail)
                finally:
                    stream_observed.set()
                    finished.set()
                    server.shutdown()
                    server.server_close()
                    thread.join()
        return requests

    @unittest.skipUnless(shutil.which("g++"), "Requires g++ for the real build and execution routes")
    def test_real_build_current_inputs_and_failed_build_invalidate_download(self):
        requests = self.exercise_browser(r"""
            el("examples").value = "teste1_calculadora_cliente_servidor.minipar";
            el("examples").dispatchEvent(new Event("change"));
            await wait(() => !el("btn-run").disabled, "Example did not finish loading");
            const currentCode = 'seq { print("UI_CURRENT_SOURCE"); '
                + 'var first = input("Primeiro: "); var second = input("Segundo: "); '
                + 'var third = input("Terceiro: "); '
                + 'print("FIRST", first); print("SECOND", second); print("THIRD", third); }';
            setSource(currentCode);
            el("program-inputs").value = "  PRIMEIRO  \n\nTERCEIRO";
            el("btn-download").click();
            await wait(() => !el("btn-download").disabled, "Build did not finish");
            assert(el("status").textContent === "Compilado", terminal());
            assert(!el("executable-link").hidden && el("executable-link").getAttribute("href"),
                "Successful build did not expose its executable link");
            assert(!terminal().includes("UI_CURRENT_SOURCE"), "Building executed the program");

            setSource("seq { var broken = ; }");
            assert(el("executable-link").hidden && !el("executable-link").getAttribute("href"),
                "Editing kept the old executable download");
            assert(!el("cpp-code").textContent && !el("tac-code").textContent,
                "Editing kept old generated artifacts");
            el("btn-download").click();
            await wait(() => !el("btn-download").disabled, "Failed build did not release controls");
            assert(el("status").textContent === "Erro", "Invalid code did not report a build failure");
            assert(el("executable-link").hidden && !el("executable-link").getAttribute("href"),
                "Failed build exposed a previous executable");

            setSource(currentCode);
            assert(el("program-inputs").value === "  PRIMEIRO  \n\nTERCEIRO", "Editing discarded manual input");
            el("btn-run").click();
            await wait(() => !el("btn-run").disabled, "Current editor code did not finish executing");
            assert(el("status").textContent === "Concluído", terminal());
            assert(terminal().includes("UI_CURRENT_SOURCE"), "Execution did not use the current editor source");
            assert(terminal().includes("FIRST   PRIMEIRO  \nSECOND \nTHIRD TERCEIRO\n"),
                "Input order, blank lines or surrounding spaces changed: " + terminal());
            el("btn-clear").click();
            assert(!el("editor-minipar").value && !el("program-inputs").value,
                "New file did not clear source and stdin");
            assert(el("executable-link").hidden, "New file kept an executable link");
        """)
        builds = [body for path, body in requests if path == "/api/build"]
        executions = [body for path, body in requests if path == "/api/execute"]
        self.assertEqual(len(builds), 2)
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0]["inputs"], ["  PRIMEIRO  ", "", "TERCEIRO"])
        self.assertIn("UI_CURRENT_SOURCE", executions[0]["code"])
        self.assertEqual([path for path, _ in requests if path in ("/api/compile", "/api/session/create")], [],
                         "Edited source must not use the legacy execution route or its example's session")

    def test_streamed_output_is_visible_before_completion_and_keeps_controls_locked(self):
        requests = self.exercise_browser(r"""
            setSource('seq { print("STREAM_FIXTURE"); }');
            el("btn-run").click();
            await wait(() => terminal().includes("PRIMEIRO ÇÃO sem nova linha"),
                "Output without a newline was not displayed before completion");
            assert(el("btn-run").disabled && el("btn-download").disabled
                && el("btn-clear").disabled && el("examples").disabled,
                "Streaming released operation controls before completion");
            assert(el("editor-minipar").readOnly, "Streaming did not keep the source snapshot locked");
            assert(el("status").textContent !== "Concluído", "Stream was completed before the first output was observed");
            await fetch("/stream-observed");
            await wait(() => !el("btn-run").disabled, "Completion did not release controls");
            assert(el("status").textContent === "Concluído", terminal());
            assert(terminal().includes("PRIMEIRO ÇÃO sem nova linha FINAL\n"), "Stream text or UTF-8 decoding was corrupted");
            assert(terminal().split("PRIMEIRO ÇÃO").length === 2, "Complete replayed output already streamed");
            assert(!el("btn-download").disabled && !el("btn-clear").disabled
                && !el("examples").disabled && !el("editor-minipar").readOnly,
                "Completion left controls locked");
        """, deterministic_stream=True)
        executions = [body for path, body in requests if path == "/api/execute"]
        self.assertEqual(len(executions), 1)
        self.assertIn("STREAM_FIXTURE", executions[0]["code"])

    @unittest.skipUnless(shutil.which("g++"), "Requires g++ for the real Fibonacci execution route")
    def test_fibonacci_example_uses_each_new_input_value(self):
        requests = self.exercise_browser(r"""
            const example = "teste2_fatorial_fibonacci_par.minipar";
            assert(Array.from(el("examples").options).some(option => option.value === example),
                "The editable-input Fibonacci example is missing from the selector");
            el("examples").value = example;
            el("examples").dispatchEvent(new Event("change"));
            await wait(() => !el("btn-run").disabled, "Fibonacci example did not finish loading");
            assert(!el("program-inputs").disabled, "The input-enabled example disabled its input field");
            const numbers = () => terminal().split("\n").map(line => line.trim())
                .filter(line => /^\d+$/.test(line)).map(Number);

            el("program-inputs").value = "5\n5";
            el("btn-run").click();
            await wait(() => !el("btn-run").disabled, "Fibonacci with five terms did not finish");
            assert(el("status").textContent === "Concluído", terminal());
            const firstOutput = terminal();
            const firstNumbers = numbers();
            assert(firstNumbers.at(-1) === 3, "Five Fibonacci terms must end in 3: " + firstOutput);

            el("program-inputs").value = "5\n8";
            el("btn-run").click();
            await wait(() => !el("btn-run").disabled, "Fibonacci with eight terms did not finish");
            assert(el("status").textContent === "Concluído", terminal());
            const secondNumbers = numbers();
            assert(secondNumbers.at(-1) === 13, "Eight Fibonacci terms must end in 13: " + terminal());
            assert(secondNumbers.length === firstNumbers.length + 3,
                "Changing the requested term count did not add three Fibonacci values");
            assert(terminal() !== firstOutput, "Changing the input reused the previous execution output");
        """)
        executions = [body for path, body in requests if path == "/api/execute"]
        self.assertEqual(len(executions), 2)
        self.assertEqual([body["inputs"] for body in executions], [["5", "5"], ["5", "8"]])
        self.assertEqual(executions[0]["code"], executions[1]["code"])
        self.assertTrue(all(body["filename"] == "teste2_fatorial_fibonacci_par.minipar" for body in executions))

    def test_fixed_example_disables_input_and_non_input_source_blocks_unused_values(self):
        requests = self.exercise_browser(r"""
            el("examples").value = "fixed-no-input.minipar";
            el("examples").dispatchEvent(new Event("change"));
            await wait(() => !el("btn-run").disabled, "Fixed example did not finish loading");
            assert(el("program-inputs").disabled, "A fixed-value example left manual stdin enabled");
            assert(el("inputs-help").textContent.includes(
                "Este programa não usa input(). Os valores dele estão definidos no código."),
                "Fixed-value example did not explain why inputs cannot affect its result");

            // A literal and a comment containing input() are not lexical INPUT tokens.
            setSource('seq { print("texto input() continua literal"); }\n# input("comentário")');
            assert(!el("program-inputs").disabled, "Editing the source did not re-enable manual inputs");
            el("program-inputs").value = "8";
            el("btn-run").click();
            await wait(() => !el("btn-run").disabled, "Input preflight did not release controls");
            assert(el("status").textContent === "Erro", "Unused input was not reported before execution");
            assert(terminal().includes("O código atual não usa input(). Os valores digitados não seriam utilizados.")
                && terminal().includes("Limpe o campo"),
                "Unused input did not produce the specific explanation: " + terminal());
            assert(!el("program-inputs").disabled, "Unused values cannot be cleared after the warning");
            assert(!terminal().includes("Execução concluída"), "The program ran despite unused input");
        """, custom_examples={"fixed-no-input.minipar": 'seq { print("FIXED_VALUE"); }'})
        self.assertEqual([body for path, body in requests if path == "/api/execute"], [],
                         "Source without an INPUT token must not be executed with unused manual values")
        analyses = [body for path, body in requests if path == "/api/analyze"]
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0]["phase"], "tokens")
        self.assertIn('"texto input() continua literal"', analyses[0]["code"])
        self.assertIn('# input("comentário")', analyses[0]["code"])


if __name__ == "__main__":
    unittest.main()
