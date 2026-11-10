"""Check executable downloads and streamed execution without a browser."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
import codecs
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import app as web
import web_execution as execution


ROOT = Path(__file__).resolve().parents[1]


def ndjson_events(response):
    decoder = codecs.getincrementaldecoder("utf-8")()
    pending = ""
    for chunk in response.response:
        pending += decoder.decode(chunk) if isinstance(chunk, bytes) else chunk
        while "\n" in pending:
            line, pending = pending.split("\n", 1)
            if line.strip():
                yield json.loads(line)
    pending += decoder.decode(b"", final=True)
    if pending.strip():
        yield json.loads(pending)


class ExecutionFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="web-execution-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.output = self.work / "builds"
        self.session = self.work / "session.json"
        self.session.write_text('{"sentinel": "existing terminal session"}', encoding="utf-8")
        self.original_session = self.session.read_bytes()
        self.check_session_unchanged = True
        patches = ExitStack()
        self.addCleanup(patches.close)
        patches.enter_context(patch.object(web, "OUTPUT_DIR", str(self.output)))
        patches.enter_context(patch("test_orchestrator.SESSION_FILE", str(self.session)))
        patches.enter_context(patch.dict(web.app.config, {
            "WEB_COMPILE_TIMEOUT": 30, "WEB_EXECUTE_TIMEOUT": 3,
        }))
        self.client = web.app.test_client()

    def tearDown(self):
        if self.check_session_unchanged:
            self.assertEqual(self.session.read_bytes(), self.original_session,
                             "An independent Web request changed a terminal session")

    def active_session(self, code):
        tests = self.work / "examples"
        tests.mkdir()
        filename = "owned.minipar"
        (tests / filename).write_text(code, encoding="utf-8")
        patch_tests = patch.object(web, "TESTS_DIR", str(tests))
        patch_tests.start()
        self.addCleanup(patch_tests.stop)
        self.session.write_text(json.dumps({
            "status": "running", "created_at": "owned-session", "test_file": filename,
            "initiator_terminal": web.get_terminal_id(),
            "progress_log": [], "participants": [],
        }), encoding="utf-8")
        self.original_session = self.session.read_bytes()
        return {"code": code, "filename": filename}

    def assert_complete(self, events, success):
        complete = [event for event in events if event["type"] == "complete"]
        self.assertEqual(len(complete), 1, events)
        self.assertIs(events[-1], complete[0])
        self.assertIs(complete[0]["success"], success, complete[0])
        self.assertIn("exit_code", complete[0])
        self.assertIn("cpp", complete[0])
        self.assertIn("tac", complete[0])
        return complete[0]


@unittest.skipUnless(shutil.which("g++"), "Requires g++ on PATH")
class RealWebExecutionTests(ExecutionFixture):
    def test_build_downloads_the_real_binary_without_running_it_or_collecting_input(self):
        code = 'seq { var answer = input("BUILD_MUST_NOT_PROMPT"); print("BUILD_MUST_NOT_RUN", answer); }'
        response = self.client.post("/api/build", json={"code": code, "filename": "download.minipar"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"], data)
        self.assertIn("BUILD_MUST_NOT_RUN", data["cpp"])
        self.assertIn("BUILD_MUST_NOT_RUN", data["tac"])
        self.assertNotIn("BUILD_MUST_NOT_RUN", data["stdout"])
        self.assertNotIn("BUILD_MUST_NOT_PROMPT", data["stdout"])
        self.assertTrue(data["download_url"])
        expected_name = "download.exe" if os.name == "nt" else "download"
        self.assertEqual(data["filename"], expected_name)

        downloaded = self.client.get(data["download_url"])
        try:
            self.assertEqual(downloaded.status_code, 200)
            self.assertIn("attachment", downloaded.headers["Content-Disposition"])
            self.assertIn(expected_name, downloaded.headers["Content-Disposition"])
            binary = next(self.output.rglob(expected_name))
            self.assertEqual(downloaded.data, binary.read_bytes())
            self.assertGreater(len(downloaded.data), 0)
        finally:
            downloaded.close()

        prefix = data["download_url"].rsplit("/", 1)[0]
        for attempted_name in ("download.cpp", "download.tac", "source/download.minipar",
                               "..%2F..%2FREADME.md", "..%5C..%5CREADME.md"):
            with self.subTest(attempted_name=attempted_name):
                denied = self.client.get(prefix + "/" + attempted_name)
                self.assertIn(denied.status_code, (400, 404))
        self.assertFalse((self.work / "download.minipar").exists())

    def test_execution_uses_supplied_input_and_finishes_with_real_artifacts(self):
        response = self.client.post("/api/execute", json={
            "code": 'seq { var answer = input("Question:"); print("ANSWER:", answer); }',
            "filename": "input.minipar", "inputs": ["minipar-input"],
        }, buffered=False)
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn("ndjson", response.content_type)
            events = list(ndjson_events(response))
        finally:
            response.close()
        complete = self.assert_complete(events, True)
        self.assertEqual(complete["exit_code"], 0)
        output = "".join(event["text"] for event in events
                         if event["type"] == "output" and event["stream"] == "stdout")
        self.assertIn("ANSWER:", output)
        self.assertIn("minipar-input", output)
        self.assertIn("ANSWER:", complete["cpp"])
        self.assertIn("ANSWER:", complete["tac"])

    def test_fibonacci_example_computes_different_sequences_from_supplied_inputs(self):
        source = ROOT / "tests" / "teste2_fatorial_fibonacci_par.minipar"
        code = source.read_text(encoding="utf-8")
        outputs = []
        for count, expected in ((5, [0, 1, 1, 2, 3]), (8, [0, 1, 1, 2, 3, 5, 8, 13])):
            with self.subTest(count=count):
                response = self.client.post("/api/execute", json={
                    "code": code, "filename": source.name, "inputs": ["5", str(count)],
                }, buffered=False)
                try:
                    self.assertEqual(response.status_code, 200)
                    events = list(ndjson_events(response))
                finally:
                    response.close()
                complete = self.assert_complete(events, True)
                self.assertEqual(complete["exit_code"], 0)
                executing = False
                runtime_output = []
                for event in events:
                    if event["type"] == "phase" and event["phase"] == "executing":
                        executing = True
                    elif executing and event["type"] == "output" and event["stream"] == "stdout":
                        runtime_output.append(event["text"])
                output = "".join(runtime_output)
                self.assertIn("Fibonacci", output)
                # The factorial and Fibonacci branches may finish in either
                # order. Only Fibonacci emits lines containing a single number.
                values = [int(line.strip()) for line in output.splitlines()
                          if line.strip().isdigit()]
                self.assertEqual(values, expected, output)
                outputs.append(output)
        self.assertNotEqual(outputs[0], outputs[1])

    def test_concurrent_builds_with_the_same_filename_keep_distinct_downloads(self):
        def build(marker):
            with web.app.test_client() as client:
                response = client.post("/api/build", json={
                    "code": f'seq {{ print("{marker}"); }}', "filename": "same.minipar",
                })
                self.assertEqual(response.status_code, 200)
                return response.get_json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(build, marker) for marker in ("FIRST_BINARY", "SECOND_BINARY")]
            results = [future.result(timeout=40) for future in futures]
        self.assertNotEqual(results[0]["download_url"], results[1]["download_url"])
        for index, result in enumerate(results):
            self.assertTrue(result["success"], result)
            own, other = ("FIRST_BINARY", "SECOND_BINARY") if index == 0 else ("SECOND_BINARY", "FIRST_BINARY")
            for field in ("cpp", "tac"):
                self.assertIn(own, result[field])
                self.assertNotIn(other, result[field])
            downloaded = self.client.get(result["download_url"])
            try:
                self.assertEqual(downloaded.status_code, 200)
                self.assertGreater(len(downloaded.data), 0)
            finally:
                downloaded.close()


class WebExecutionBoundaryTests(ExecutionFixture):
    @contextmanager
    def controlled_runtime(self, script="", compiler_result=None):
        """Use a deterministic child while keeping the actual pipe/HTTP stream."""
        prepared = []
        children = []
        real_prepare = execution.prepare_run
        real_iterator = execution.iter_process
        real_popen = subprocess.Popen
        compile_result = compiler_result or execution.ProcessResult(0, "Compiled fixture.\n", "")

        def prepare(*args, **kwargs):
            run = real_prepare(*args, **kwargs)
            prepared.append(run)
            return run

        def start(command, **kwargs):
            if prepared and Path(command[0]) == prepared[-1].executable:
                child = real_popen([sys.executable, "-X", "utf8", "-u", "-c", script], **kwargs)
                children.append(child)
                return child
            return real_popen(command, **kwargs)

        def process(command, **options):
            if any(Path(str(argument)).name == "main.py" for argument in command):
                run = prepared[-1]
                if compile_result.exit_code == 0 and not compile_result.timed_out:
                    run.executable.write_bytes(b"test executable; runtime is substituted")
                    (run.directory / (run.stem + ".cpp")).write_text("C++ fixture", encoding="utf-8")
                    (run.directory / (run.stem + ".tac")).write_text("TAC fixture", encoding="utf-8")
                for stream in ("stdout", "stderr"):
                    text = getattr(compile_result, stream)
                    if text:
                        yield {"type": "output", "stream": stream, "text": text}
                return compile_result
            return (yield from real_iterator(command, **options))

        try:
            with patch.object(execution, "prepare_run", side_effect=prepare), \
                    patch.object(execution, "iter_process", side_effect=process), \
                    patch.object(execution.subprocess, "Popen", side_effect=start):
                yield children
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=3)

    def test_invalid_source_names_and_inputs_are_rejected_before_creating_a_run(self):
        valid = self.active_session("seq { print(1); }")
        invalid = [None, [], "code", {}, {"filename": "valid.minipar"}]
        invalid.extend({**valid, "code": value} for value in (None, False, 42, [], "", " \n\t"))
        invalid.extend({**valid, "filename": value} for value in (
            None, 42, "../escape.minipar", "..\\escape.minipar", "C:\\escape.minipar",
            "bad\r\n.minipar", "source.txt", "CON.minipar",
        ))
        with patch.object(execution, "prepare_run", side_effect=AssertionError("Invalid request created artifacts")):
            for endpoint in ("/api/build", "/api/execute"):
                for payload in invalid:
                    with self.subTest(endpoint=endpoint, payload=payload):
                        response = self.client.post(endpoint, data=json.dumps(payload), content_type="application/json")
                        self.assertEqual(response.status_code, 400)
                        self.assertTrue(response.get_json()["error"])
                for raw, content_type in (("{", "application/json"), ("not JSON", "text/plain")):
                    with self.subTest(endpoint=endpoint, raw=raw):
                        response = self.client.post(endpoint, data=raw, content_type=content_type)
                        self.assertEqual(response.status_code, 400)
            for inputs in (None, "answer", [1], {"value": "answer"}):
                with self.subTest(inputs=inputs):
                    response = self.client.post("/api/execute", json={**valid, "inputs": inputs})
                    self.assertEqual(response.status_code, 400)
        self.assertFalse(self.output.exists())

    def test_only_registered_executables_can_be_downloaded(self):
        private = self.output / "runs" / "run-private"
        private.mkdir(parents=True)
        (private / "private.exe").write_bytes(b"not registered")
        response = self.client.get("/api/download/" + "a" * 43 + "/private.exe")
        self.assertEqual(response.status_code, 404)

    def test_input_mentions_in_strings_or_comments_do_not_consume_supplied_inputs(self):
        programs = ('seq { print("input()"); }', '# input() is only a comment\nseq { print(1); }')
        with patch.object(execution, "prepare_run", side_effect=AssertionError("Unused inputs started a build")):
            for code in programs:
                with self.subTest(code=code):
                    response = self.client.post("/api/execute", json={"code": code, "inputs": ["30"]})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("não usa input()", response.get_json()["error"])
        self.assertFalse(self.output.exists())

    def test_build_does_not_update_even_a_matching_active_terminal_session(self):
        payload = self.active_session("seq { print(1); }")
        payload["inputs"] = ["ignored by compile-only build"]
        with self.controlled_runtime() as children:
            data = self.client.post("/api/build", json=payload).get_json()
        self.assertTrue(data["success"], data)
        self.assertEqual(children, [], "Build started a runtime process")

    def test_compiler_failure_never_publishes_a_download_or_previous_artifacts(self):
        with self.controlled_runtime():
            good = self.client.post("/api/build", json={
                "code": 'seq { print("OLD_SOURCE"); }', "filename": "same.minipar",
            }).get_json()
        self.assertTrue(good["success"], good)
        for bad_source in ("seq { var value = ; }", "seq { print(1); @ }"):
            with self.subTest(code=bad_source):
                failed = self.client.post("/api/build", json={"code": bad_source, "filename": "same.minipar"})
                self.assertEqual(failed.status_code, 200)
                data = failed.get_json()
                self.assertFalse(data["success"], data)
                self.assertFalse(data["download_url"])
                self.assertTrue(data["stderr"])
                self.assertEqual(data["cpp"], "")
                self.assertEqual(data["tac"], "")
                response = self.client.post("/api/execute", json={
                    "code": bad_source, "filename": "same.minipar",
                    "inputs": ["30"] if "@" in bad_source else [],
                }, buffered=False)
                try:
                    events = list(ndjson_events(response))
                finally:
                    response.close()
                complete = self.assert_complete(events, False)
                self.assertEqual(complete["cpp"], "")
                self.assertEqual(complete["tac"], "")

    def test_compiler_timeout_never_starts_the_runtime_or_offers_a_download(self):
        failed = execution.ProcessResult(None, "", "", timed_out=True)
        with self.controlled_runtime(compiler_result=failed) as children:
            data = self.client.post("/api/build", json={"code": "seq {}"}).get_json()
            self.assertFalse(data["success"], data)
            self.assertFalse(data["download_url"])
            response = self.client.post("/api/execute", json={"code": "seq {}"}, buffered=False)
            try:
                events = list(ndjson_events(response))
            finally:
                response.close()
            self.assert_complete(events, False)
            self.assertEqual(children, [])

    def test_execution_preserves_other_terminal_sessions_and_inactive_sessions(self):
        payload = self.active_session("seq { print(1); }")
        session = json.loads(self.session.read_text(encoding="utf-8"))
        for state, owner in (("running", "another-terminal"),
                             ("completed", web.get_terminal_id()),
                             ("cancelled", web.get_terminal_id())):
            with self.subTest(state=state, owner=owner):
                session.update(status=state, initiator_terminal=owner)
                self.session.write_text(json.dumps(session), encoding="utf-8")
                self.original_session = self.session.read_bytes()
                with self.controlled_runtime("print('INDEPENDENT',flush=True)"):
                    response = self.client.post("/api/execute", json=payload, buffered=False)
                    try:
                        events = list(ndjson_events(response))
                    finally:
                        response.close()
                self.assert_complete(events, True)
                self.assertEqual(self.session.read_bytes(), self.original_session)

    def test_stdout_is_received_while_the_child_is_still_running_without_a_newline(self):
        script = "import sys,time;sys.stdout.write('EARLY');sys.stdout.flush();time.sleep(0.8);print('LATE',flush=True)"
        with self.controlled_runtime(script) as children:
            response = self.client.post("/api/execute", json={"code": "seq { print(1); }"}, buffered=False)
            received = []
            stdout = ""
            early_at = None
            try:
                for event in ndjson_events(response):
                    received.append(event)
                    if event["type"] == "output" and event["stream"] == "stdout":
                        stdout += event["text"]
                        if early_at is None and "EARLY" in stdout:
                            early_at = time.monotonic()
                            self.assertEqual(len(children), 1)
                            self.assertIsNone(children[0].poll(), "Output was buffered until the process exited")
                            self.assertNotIn("LATE", stdout)
                completed_at = time.monotonic()
            finally:
                response.close()
            self.assertIsNotNone(early_at, received)
            self.assertGreater(completed_at - early_at, 0.4, "No interval separated early output from completion")
            self.assertIn("LATE", stdout)
            self.assertEqual(self.assert_complete(received, True)["exit_code"], 0)

    def test_nonzero_runtime_exit_is_a_failed_complete_event_with_stderr(self):
        script = "import sys;sys.stderr.write('RUNTIME_FAILURE');sys.stderr.flush();sys.exit(7)"
        payload = self.active_session("seq { print(1); }")
        self.check_session_unchanged = False
        with self.controlled_runtime(script):
            response = self.client.post("/api/execute", json=payload, buffered=False)
            try:
                events = list(ndjson_events(response))
            finally:
                response.close()
        complete = self.assert_complete(events, False)
        self.assertEqual(complete["exit_code"], 7)
        stderr = "".join(event["text"] for event in events
                         if event["type"] == "output" and event["stream"] == "stderr")
        self.assertIn("RUNTIME_FAILURE", stderr)
        self.assertEqual(json.loads(self.session.read_text(encoding="utf-8"))["status"], "cancelled")

    def test_runtime_timeout_terminates_the_child_and_ends_the_stream(self):
        with patch.dict(web.app.config, {"WEB_EXECUTE_TIMEOUT": 0.2}), \
                self.controlled_runtime("import time;time.sleep(60)") as children:
            response = self.client.post("/api/execute", json={"code": "seq { print(1); }"}, buffered=False)
            try:
                events = list(ndjson_events(response))
            finally:
                response.close()
            self.assert_complete(events, False)
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll(), "A timed-out process survived the response")

    def test_excessive_output_is_bounded_and_terminates_the_child(self):
        script = "import sys,time;sys.stdout.write('X'*8192);sys.stdout.flush();time.sleep(60)"
        with patch.dict(web.app.config, {"WEB_OUTPUT_LIMIT": 128}), \
                self.controlled_runtime(script) as children:
            response = self.client.post("/api/execute", json={"code": "seq {}"}, buffered=False)
            try:
                events = list(ndjson_events(response))
            finally:
                response.close()
            self.assert_complete(events, False)
            output = "".join(event["text"] for event in events if event["type"] == "output")
            self.assertGreater(output.count("X"), 0)
            self.assertLessEqual(output.count("X"), 128)
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll(), "An output-limited process survived the response")

    def test_disconnecting_the_client_terminates_the_running_process(self):
        script = "import time;print('RUNNING',flush=True);time.sleep(60)"
        payload = self.active_session("seq { print(1); }")
        self.check_session_unchanged = False
        with self.controlled_runtime(script) as children:
            response = self.client.post("/api/execute", json=payload, buffered=False)
            try:
                stdout = ""
                for event in ndjson_events(response):
                    if event["type"] == "output" and event["stream"] == "stdout":
                        stdout += event["text"]
                    if "RUNNING" in stdout:
                        break
                self.assertEqual(len(children), 1)
                self.assertIsNone(children[0].poll())
            finally:
                response.close()
            children[0].wait(timeout=2)
            self.assertIsNotNone(children[0].poll(), "Disconnect left a live child process")
        self.assertEqual(json.loads(self.session.read_text(encoding="utf-8"))["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
