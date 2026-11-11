"""Real compiler checks: same filenames must keep their own source and artifacts."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import app as web
import menu
from run_artifacts import executable_path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("g++"), "Requires g++ on PATH")
class OutputIsolationTests(unittest.TestCase):
    def test_concurrent_web_and_cli_runs_with_same_filename(self):
        (ROOT / "output").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="isolation-test-") as tmp:
            tmp = Path(tmp)
            output = tmp / "output"
            source = tmp / "same.minipar"
            source.write_text('seq { print("TERMINAL_MARKER"); }', encoding="utf-8")

            def web_run(marker):
                with web.app.test_client() as client:
                    return client.post("/api/compile", json={
                        "filename": "same.minipar",
                        "code": f'seq {{ print("{marker}"); }}',
                    })

            def cli_run():
                return subprocess.run(
                    [sys.executable, str(ROOT / "main.py"), str(source)],
                    cwd=tmp, capture_output=True, text=True, timeout=60,
                )

            with ExitStack() as stack:
                stack.enter_context(patch.object(web, "OUTPUT_DIR", str(output)))
                # Keep these artifact tests independent of any real terminal session.
                for name in ("set_session_phase", "append_session_log", "record_execution_output", "finalize_test_execution"):
                    stack.enter_context(patch.object(web, name))
                with ThreadPoolExecutor(max_workers=3) as pool:
                    first = pool.submit(web_run, "WEB_FIRST_MARKER")
                    second = pool.submit(web_run, "WEB_SECOND_MARKER")
                    terminal = pool.submit(cli_run)
                    responses = [first.result(), second.result()]
                    cli = terminal.result()

                for response, own, other in (
                    (responses[0], "WEB_FIRST_MARKER", "WEB_SECOND_MARKER"),
                    (responses[1], "WEB_SECOND_MARKER", "WEB_FIRST_MARKER"),
                ):
                    self.assertEqual(response.status_code, 200)
                    data = response.get_json()
                    self.assertTrue(data["success"], data)
                    for field in ("stdout", "cpp", "tac"):
                        self.assertIn(own, data[field])
                        self.assertNotIn(other, data[field])
                        self.assertNotIn("TERMINAL_MARKER", data[field])

                self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
                run_dir = next(line.removeprefix("[OUTPUT] ") for line in cli.stdout.splitlines() if line.startswith("[OUTPUT] "))
                for name in ("set_session_phase", "append_session_log", "record_execution_output"):
                    stack.enter_context(patch.object(menu, name))
                result = menu.executar_binario("same", output_dir=run_dir)
                self.assertEqual(result.strip(), "TERMINAL_MARKER")

                runs = list((output / "runs").iterdir())
                self.assertEqual(len(runs), 3)
                for run in runs:
                    self.assertTrue((run / "same.cpp").is_file())
                    self.assertTrue((run / "same.tac").is_file())
                    self.assertTrue(Path(executable_path(str(run), "same")).is_file())

                # A later failed compile must not show a previous run's C++ or TAC.
                with web.app.test_client() as client:
                    failed = client.post("/api/compile", json={
                        "filename": "same.minipar", "code": "seq { var x = ; }",
                    }).get_json()
                self.assertFalse(failed["success"])
                self.assertEqual(failed["cpp"], "")
                self.assertEqual(failed["tac"], "")

    def test_terminal_menu_passes_its_run_directory_to_execution(self):
        with patch.object(menu, "_exibir_info_teste"), patch.object(menu, "prepare_test_execution", return_value=(True, False, False)), patch.object(menu, "create_run_dir", return_value="private-run"), patch.object(menu, "compile_file", return_value=True) as compile_program, patch.object(menu, "executar_binario", return_value="ok") as execute, patch.object(menu, "finalize_test_execution"), patch.object(menu, "set_session_phase"), patch.object(menu, "append_session_log"):
            menu.rodar_teste("tests/same.minipar")
        compile_program.assert_called_once_with("tests/same.minipar", "same", "private-run")
        execute.assert_called_once_with("same", interactive=False, output_dir="private-run")


if __name__ == "__main__":
    unittest.main()
