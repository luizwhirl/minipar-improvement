"""Compile the unchanged official Fork/Join scenarios and check their full output."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from program_analyzer import get_program_spec
from run_artifacts import executable_path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("g++"), "g++ is required for executable integration tests")
class OfficialForkJoinExampleTests(unittest.TestCase):
    def check_official_example(self, filename):
        source = ROOT / "tests" / filename
        expected = (ROOT / "tests" / "expected_results" / (source.stem + ".expected.txt"))
        metadata = get_program_spec(str(source))
        self.assertFalse(metadata["requires_input"], filename)
        self.assertEqual(metadata["input_count"], 0, filename)

        # Explicit output directories keep generated C++, binaries and run
        # metadata separate from any browser or terminal session in progress.
        output = ROOT / "output"
        output.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="official-fork-join-", dir=output) as temporary:
            directory = Path(temporary) / source.stem
            compiled = subprocess.run([
                sys.executable, "-X", "utf8", "-B", str(ROOT / "main.py"),
                str(source), source.stem, "--output-dir", str(directory),
            ], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            executed = subprocess.run(
                [executable_path(str(directory), source.stem)],
                input="", cwd=ROOT, capture_output=True, text=True,
                encoding="utf-8", timeout=45,
            )
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
            self.assertEqual(executed.stderr, "", executed.stderr)
            # These fixtures contain no wall-clock fields. Universal newline
            # handling is the only normalization; spaces and blank lines matter.
            self.assertEqual(executed.stdout, expected.read_text(encoding="utf-8"))

    def test_four_core_evaluation_matches_official_result(self):
        self.check_official_example("teste8_avaliacao_4_nucleos.minipar")

    def test_five_core_mandelbrot_matches_official_result(self):
        self.check_official_example("teste9_avaliacao_5_nucleos_mandelbrot.minipar")

    def test_six_core_two_fractals_match_official_result(self):
        self.check_official_example("teste10_avaliacao_6_nucleos_2_fractais.minipar")


if __name__ == "__main__":
    unittest.main()
