"""Exercise the local AST graph against the real analysis worker in Edge."""
import html
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from werkzeug.serving import make_server

import app as web


ROOT = Path(__file__).resolve().parents[1]
EDGE = Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe"


@unittest.skipUnless(EDGE.is_file(), "Requires Microsoft Edge; no C++ compiler is needed")
class ASTViewerTests(unittest.TestCase):
    def test_graph_interaction_json_and_invalidation_use_the_real_ast(self):
        finished = threading.Event()
        compile_requests = []
        actions = r"""
        document.addEventListener("DOMContentLoaded", async () => {
            const el = id => document.getElementById(id);
            const assert = (condition, message) => { if (!condition) throw Error(message); };
            const wait = async (check, message) => {
                for (let attempt = 0; attempt < 400; attempt++) {
                    if (check()) return;
                    await new Promise(done => setTimeout(done, 50));
                }
                throw Error(message || "AST interaction timed out");
            };
            const setSource = code => {
                el("editor-minipar").value = code;
                el("editor-minipar").dispatchEvent(new Event("input", { bubbles: true }));
            };
            const graph = () => document.querySelector(".ast-svg");
            const nodes = () => Array.from(document.querySelectorAll(".ast-svg .ast-node"));
            const control = action => document.querySelector(`#ast-result [data-action="${action}"]`);
            try {
                await wait(() => el("examples").options.length > 1, "Examples did not load");
                setSource("seq {\n    var x = 2 + 3;\n    print(x);\n}");
                el("tab-ast").click();
                await wait(() => graph() && nodes().length >= 1, el("ast-feedback").textContent);
                control("expand-all").click();
                await wait(() => nodes().some(node => node.dataset.nodeType === "BinaryExpr"),
                    "Expanding the AST did not reveal its expression nodes");
                const initialCount = nodes().length;
                assert(!el("out-ast").hidden, "AST panel is hidden");
                assert(nodes().some(node => node.dataset.nodeType === "BinaryExpr"), "Binary expression was omitted");

                const jsonDetails = document.querySelector("#ast-result details.ast-json");
                assert(jsonDetails, "JSON fallback is missing");
                jsonDetails.querySelector("summary").click();
                assert(jsonDetails.open && el("ast-code").textContent.includes('"node_type": "Program"'), "AST JSON is unavailable");

                const declaration = nodes().find(node => node.dataset.nodeType === "VarDecl");
                assert(declaration, "Variable declaration node is missing");
                declaration.dispatchEvent(new MouseEvent("click", { bubbles: true }));
                const inspector = document.querySelector("#ast-result .ast-inspector");
                await wait(() => declaration.classList.contains("is-selected"), "Node selection failed");
                assert(inspector && /linha\s*:?\s*2/i.test(inspector.textContent), "Selected node source line is missing");
                assert(inspector.textContent.includes("x"), "Selected node attributes are missing");

                control("collapse-all").click();
                await wait(() => nodes().length < initialCount, "Collapsing branches had no effect");
                control("expand-all").click();
                await wait(() => nodes().length >= initialCount, "Expanding branches lost AST nodes");
                const canvas = () => document.querySelector(".ast-svg .ast-canvas");
                const originalTransform = canvas().getAttribute("transform");
                control("zoom-in").click();
                await wait(() => canvas().getAttribute("transform") !== originalTransform, "Zoom did not change the graph");

                control("enlarge").click();
                await wait(() => document.querySelector("dialog.ast-dialog[open]"), "Expanded view did not open");
                const dialog = document.querySelector("dialog.ast-dialog[open]");
                assert(dialog.querySelector(".ast-svg"), "Expanded view has no graph");
                assert(document.querySelectorAll(".ast-svg").length === 1, "Expanded view duplicated the graph");
                const close = Array.from(dialog.querySelectorAll("button")).find(button =>
                    button.getAttribute("aria-label") === "Fechar visualização ampliada");
                assert(close, "Expanded view has no accessible close control");
                close.click();
                await wait(() => !document.querySelector("dialog.ast-dialog[open]")
                    && document.querySelector("#ast-result .ast-svg"), "Expanded view did not restore the graph");

                setSource("seq {\n    var x = ;\n}");
                await wait(() => !graph(), "Editing kept the previous graph alive");
                assert(!el("ast-code") || !el("ast-code").textContent, "Editing kept stale AST JSON");
                el("tab-ast").click();
                await wait(() => !el("ast-diagnostics").hidden && el("ast-diagnostics").textContent.trim(),
                    "Invalid syntax did not produce diagnostics");
                assert(!graph(), "A failed analysis left stale graph nodes");
                assert(!el("ast-code") || !el("ast-code").textContent, "A failed analysis left stale AST JSON");

                el("tab-tokens").click();
                await wait(() => document.querySelector("#tokens-result tbody tr"), "Tokens stopped working after an AST error");
                assert(!el("out-tokens").hidden, "Switching to Tokens failed");

                const unsafeText = '<img src=x onerror="window.astInjected=true">';
                setSource('seq { print("' + unsafeText.replaceAll('"', '\\"') + '"); }');
                el("tab-ast").click();
                await wait(() => nodes().some(node => node.dataset.nodeType === "StringExpr"), "String AST was not rendered");
                nodes().find(node => node.dataset.nodeType === "StringExpr")
                    .dispatchEvent(new MouseEvent("click", { bubbles: true }));
                assert(document.querySelector("#ast-result .ast-inspector").textContent.includes(unsafeText),
                    "String content was discarded from node details");
                assert(!document.querySelector("#ast-result img") && !window.astInjected, "AST text was interpreted as HTML");
                document.body.dataset.testResult = "passed";
            } catch (error) {
                document.body.dataset.testResult = "failed";
                document.body.dataset.testError = error.stack || String(error);
            } finally { await fetch("/finished"); }
        });
        """
        original = web.app.wsgi_app

        def fixture(environ, respond):
            path = environ["PATH_INFO"]
            if path in ("/hold", "/finished"):
                if path == "/hold":
                    finished.wait(55)
                else:
                    finished.set()
                respond("200 OK", [("Content-Type", "text/plain")])
                return [b""]
            if path == "/api/compile":
                compile_requests.append(path)
            if path == "/":
                with web.app.test_request_context("/"):
                    page = web.index()
                # Remove only the external CodeMirror CDN. D3, model and viewer
                # remain the local production scripts, with real worker responses.
                page = "\n".join(line for line in page.splitlines() if "cdnjs.cloudflare.com" not in line)
                page = page.replace("</body>", '<img src="/hold"><script>' + actions + "</script></body>")
                respond("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                return [page.encode("utf-8")]
            return original(environ, respond)

        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="ast-viewer-test-") as tmp:
            work = Path(tmp)
            with patch.object(web, "OUTPUT_DIR", str(work / "compiler-output")), \
                    patch("test_orchestrator.SESSION_FILE", str(work / "session.json")):
                server = make_server("127.0.0.1", 0, fixture, threaded=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    browser = subprocess.run([
                        str(EDGE), "--headless", "--disable-gpu", "--no-first-run",
                        "--disable-background-networking", "--disable-extensions",
                        "--user-data-dir=" + str(work / "edge"), "--dump-dom",
                        f"http://127.0.0.1:{server.server_port}/",
                    ], capture_output=True, timeout=65)
                    dom = browser.stdout.decode("utf-8", errors="replace")
                    failure = re.search(r'data-test-error="([^"]*)"', dom)
                    detail = html.unescape(failure.group(1)) if failure else (
                        f"Edge exit code: {browser.returncode}\n"
                        + browser.stderr.decode("utf-8", errors="replace")[-3000:] + dom[-4000:])
                    self.assertIn('data-test-result="passed"', dom, detail)
                    self.assertEqual(compile_requests, [], "Inspecting AST must not compile or execute the program")
                    self.assertFalse((work / "compiler-output").exists())
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()


if __name__ == "__main__":
    unittest.main()
