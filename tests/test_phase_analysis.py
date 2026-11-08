"""Exercise phase inspection without a browser, compiler executable or program run."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import app as web
import analysis_worker as analysis


ROOT = Path(__file__).resolve().parents[1]
PHASES = ("tokens", "ast", "semantic", "tac", "cpp")


class PhaseAnalysisTests(unittest.TestCase):
    def analyze(self, code, phase):
        with web.app.test_client() as client:
            response = client.post("/api/analyze", json={"code": code, "phase": phase})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        data = response.get_json()
        self.assertEqual(data["phase"], phase)
        self.assertIsInstance(data["success"], bool)
        self.assertIsInstance(data["diagnostics"], list)
        self.assertIn("failed_phase", data)
        self.assertIn("result", data)
        self.assertNotIn("Traceback", response.get_data(as_text=True))
        return data

    def assert_success(self, data):
        self.assertTrue(data["success"], data)
        self.assertIsNone(data["failed_phase"])
        self.assertEqual(data["diagnostics"], [])
        self.assertIsNotNone(data["result"])

    def assert_failure(self, data, failed_phase):
        self.assertFalse(data["success"], data)
        self.assertEqual(data["failed_phase"], failed_phase)
        self.assertTrue(data["diagnostics"], data)
        for error in data["diagnostics"]:
            self.assertEqual(error["phase"], failed_phase)
            self.assertEqual(error["severity"], "error")
            self.assertTrue(error["message"])
            self.assertIn("line", error)
            self.assertIn("column", error)
        if data["phase"] != "tokens":
            self.assertIsNone(data["result"], "A failed prerequisite must not expose generated code")

    def test_tokens_are_available_even_when_the_program_has_invalid_syntax(self):
        code = "seq { var value = ; }"
        data = self.analyze(code, "tokens")
        self.assert_success(data)
        tokens = data["result"]["tokens"]
        self.assertTrue(any(token["type"] == "VAR" for token in tokens))
        self.assertTrue(any(token["lexeme"] == "value" for token in tokens))
        for token in tokens:
            self.assertIsInstance(token["type"], str)
            self.assertIsInstance(token["lexeme"], str)
            self.assertGreaterEqual(token["line"], 1)
            self.assertGreaterEqual(token["column"], 1)
        self.assert_failure(self.analyze(code, "ast"), "ast")

    def test_ast_is_structured_and_does_not_require_semantic_success(self):
        code = "seq { print(undeclared_value); }"
        data = self.analyze(code, "ast")
        self.assert_success(data)
        program = data["result"]
        self.assertEqual(program["node_type"], "Program")
        block = program["statements"][0]
        self.assertEqual(block["node_type"], "SeqBlock")
        argument = block["statements"][0]["arguments"][0]
        self.assertEqual(argument["node_type"], "IdentifierExpr")
        self.assertEqual(argument["name"], "undeclared_value")
        self.assert_failure(self.analyze(code, "semantic"), "semantic")

    def test_semantic_success_is_an_explicit_validation_result(self):
        data = self.analyze("seq { var value = 7; print(value); }", "semantic")
        self.assert_success(data)
        self.assertIs(data["result"]["valid"], True)
        self.assertTrue(data["result"]["message"])

    def test_lexical_errors_include_the_source_position_and_stop_later_phases(self):
        code = "seq {\n    @\n}"
        for phase in PHASES:
            with self.subTest(phase=phase):
                data = self.analyze(code, phase)
                self.assert_failure(data, "tokens")
                error = data["diagnostics"][0]
                self.assertEqual((error["line"], error["column"]), (2, 5))
                if phase == "tokens" and data["result"] is not None:
                    self.assertIsInstance(data["result"]["tokens"], list)

    def test_unterminated_string_is_a_lexical_error(self):
        data = self.analyze('seq { print("unfinished); }', "tokens")
        self.assert_failure(data, "tokens")
        self.assertEqual(data["diagnostics"][0]["line"], 1)
        self.assertGreater(data["diagnostics"][0]["column"], 1)

    def test_syntax_errors_stop_semantics_and_both_code_generators(self):
        code = "seq {\n    var value = ;\n}"
        for phase in ("ast", "semantic", "tac", "cpp"):
            with self.subTest(phase=phase):
                data = self.analyze(code, phase)
                self.assert_failure(data, "ast")
                self.assertEqual(data["diagnostics"][0]["line"], 2)

    def test_semantic_errors_stop_both_code_generators(self):
        code = "seq {\n    print(undeclared_value);\n}"
        for phase in ("semantic", "tac", "cpp"):
            with self.subTest(phase=phase):
                data = self.analyze(code, phase)
                self.assert_failure(data, "semantic")
                self.assertIn("undeclared_value", data["diagnostics"][0]["message"])
                self.assertEqual(data["diagnostics"][0]["line"], 2)

    def test_code_generation_neither_reads_input_nor_executes_an_infinite_loop(self):
        code = 'seq { var answer = input("Question:"); while (true) { print(answer); } }'
        # Python is invoked by absolute path. No external compiler is available.
        with patch.dict(os.environ, {"PATH": ""}):
            tac = self.analyze(code, "tac")
            cpp = self.analyze(code, "cpp")
        self.assert_success(tac)
        self.assert_success(cpp)
        self.assertIsInstance(tac["result"], str)
        self.assertIn("input", tac["result"])
        self.assertIn("goto", tac["result"])
        self.assertIn("while", cpp["result"])
        self.assertIn("Question:", cpp["result"])

    def test_cpp_text_generation_does_not_invoke_a_compiler_or_write_files(self):
        program = analysis.Parser(analysis.Lexer('seq { print("TEXT_ONLY"); }').tokenize()).parse()
        with patch("codegen.subprocess.run", side_effect=AssertionError("Compiler invoked")), \
                patch("builtins.open", side_effect=AssertionError("File opened")):
            result = analysis.CppCodeGenerator().generate_text(program)
        self.assertIsInstance(result, str)
        self.assertIn("TEXT_ONLY", result)
        self.assertIn("int main", result)

    def test_shared_cpp_generator_rejects_fork_join_before_creating_artifacts(self):
        sources = {
            "fork": "func work() { return 42; } seq { fork work(); }",
            "join": "func wait_for(task) { var answer = join(task); return answer; } seq { print(1); }",
        }
        programs = {
            operation: analysis.Parser(analysis.Lexer(code).tokenize()).parse()
            for operation, code in sources.items()
        }
        with patch("codegen.subprocess.run", side_effect=AssertionError("Compiler invoked")) as compiler, \
                patch("builtins.open", side_effect=AssertionError("File opened")) as files, \
                patch("codegen.os.makedirs", side_effect=AssertionError("Directory created")) as directories:
            for operation, program in programs.items():
                with self.subTest(operation=operation):
                    generator = analysis.CppCodeGenerator()
                    with self.assertRaisesRegex(NotImplementedError, operation):
                        generator.generate_text(program)
                    errors = io.StringIO()
                    with redirect_stderr(errors):
                        self.assertIs(generator.generate(program, "unsupported"), False)
                    self.assertIn(operation, errors.getvalue().lower())
            compiler.assert_not_called()
            files.assert_not_called()
            directories.assert_not_called()

    def test_fork_join_can_be_inspected_before_cpp_support_is_implemented(self):
        code = "func double_value(value) { return value * 2; }\n" \
               "seq { var task = fork double_value(3); var answer = join(task); print(answer); }"
        tokens = self.analyze(code, "tokens")
        self.assert_success(tokens)
        kinds = {token["type"] for token in tokens["result"]["tokens"]}
        self.assertTrue({"FORK", "JOIN"}.issubset(kinds))
        ast = self.analyze(code, "ast")
        self.assert_success(ast)
        serialized = json.dumps(ast["result"])
        self.assertIn('"node_type": "ForkExpr"', serialized)
        self.assertIn('"node_type": "JoinExpr"', serialized)
        tac = self.analyze(code, "tac")
        self.assert_success(tac)
        self.assertIn("spawn double_value", tac["result"])
        self.assertIn("join task", tac["result"])
        cpp = self.analyze(code, "cpp")
        self.assert_failure(cpp, "cpp")
        self.assertTrue(any("fork" in error["message"].lower() for error in cpp["diagnostics"]))

    def test_invalid_requests_are_rejected_before_starting_the_worker(self):
        valid = {"code": "seq { print(1); }", "phase": "tokens"}
        invalid = [None, [], "program", 7, {}, {"phase": "tokens"}, {"code": valid["code"]}]
        invalid.extend({**valid, "code": code} for code in (None, False, 42, [], {}, "", " \n\t"))
        invalid.extend({**valid, "phase": phase} for phase in (None, False, [], {}, "", "run"))
        with patch.object(web.subprocess, "run", side_effect=AssertionError("Invalid request started worker")):
            with web.app.test_client() as client:
                for payload in invalid:
                    with self.subTest(payload=payload):
                        response = client.post("/api/analyze", data=json.dumps(payload), content_type="application/json")
                        self.assertEqual(response.status_code, 400)
                        self.assertTrue(response.get_json()["error"])
                for body, content_type in (("{", "application/json"), ("not JSON", "text/plain")):
                    with self.subTest(body=body):
                        response = client.post("/api/analyze", data=body, content_type=content_type)
                        self.assertEqual(response.status_code, 400)
                        self.assertTrue(response.get_json()["error"])

    def test_worker_timeout_is_reported_without_a_traceback(self):
        with patch.object(web.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 15)):
            with web.app.test_client() as client:
                response = client.post("/api/analyze", json={"code": "seq {}", "phase": "ast"})
        self.assertEqual(response.status_code, 504)
        self.assertTrue(response.get_json()["error"])
        self.assertNotIn("Traceback", response.get_data(as_text=True))

    def test_worker_crashes_or_invalid_output_are_reported_without_internal_details(self):
        internal = "Traceback: private/worker/source.py"
        results = [
            subprocess.CompletedProcess("worker", 1, "", internal),
            subprocess.CompletedProcess("worker", 0, internal, ""),
            subprocess.CompletedProcess("worker", 0, "[]", ""),
            subprocess.CompletedProcess("worker", 0, "{}", ""),
            subprocess.CompletedProcess("worker", 0, json.dumps({
                "phase": "cpp", "success": True, "result": "unexpected", "failed_phase": None,
                "diagnostics": []}), ""),
        ]
        with patch.object(web.app.logger, "error"), patch.object(web.app.logger, "exception"):
            for result in results:
                with self.subTest(returncode=result.returncode, stdout=result.stdout):
                    with patch.object(web.subprocess, "run", return_value=result):
                        with web.app.test_client() as client:
                            response = client.post("/api/analyze", json={"code": "seq {}", "phase": "ast"})
                    self.assertEqual(response.status_code, 500)
                    self.assertTrue(response.get_json()["error"])
                    self.assertNotIn("Traceback", response.get_data(as_text=True))
                    self.assertNotIn("private/worker", response.get_data(as_text=True))

    def test_concurrent_requests_keep_their_results_separate_without_artifacts_or_sessions(self):
        ready = threading.Barrier(2)
        markers = ("PRIMEIRO_Á", "SEGUNDO_B")

        def request(marker):
            ready.wait(timeout=10)
            return self.analyze(f'seq {{ print("{marker}"); }}', "cpp")

        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="analysis-test-") as tmp:
            work = Path(tmp)
            with ExitStack() as stack:
                stack.enter_context(patch.object(web, "OUTPUT_DIR", str(work / "output")))
                stack.enter_context(patch.object(web, "TEMP_DIR", str(work / "source")))
                for name in ("create_run_dir", "create_session", "clear_session", "set_session_phase",
                             "append_session_log", "record_execution_output", "finalize_test_execution", "_save_session"):
                    stack.enter_context(patch.object(web, name, side_effect=AssertionError("Analysis mutated execution state")))
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(request, marker) for marker in markers]
                    responses = [future.result(timeout=25) for future in futures]
            for index, data in enumerate(responses):
                self.assert_success(data)
                self.assertIn(markers[index], data["result"])
                self.assertNotIn(markers[1 - index], data["result"])
            self.assertEqual(list(work.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
