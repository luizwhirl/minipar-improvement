"""Compile every example and verify its algorithm uses different keyboard data."""
from pathlib import Path
from contextlib import ExitStack
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

import analysis_worker as analysis
from program_analyzer import get_program_spec
from run_artifacts import executable_path


ROOT = Path(__file__).resolve().parents[1]
HISTORY = ["1", "0", "0", "0", "0", "1", "0", "0", "0", "1", "0", "0", "1", "0", "0", "0"]

# Each variant describes real execution input and a result of the computation,
# rather than merely requiring the program to echo the supplied values.
CASES = {
    "teste1_calculadora_cliente_servidor.minipar": (
        (["+", "2", "3"], "calculator", 5),
        (["*", "4", "6"], "calculator", 24),
    ),
    "teste2_fatorial_fibonacci_par.minipar": (
        (["5", "8"], "factorial_fibonacci", (120, [0, 1, 1, 2, 3, 5, 8, 13])),
        (["6", "5"], "factorial_fibonacci", (720, [0, 1, 1, 2, 3])),
    ),
    "teste3_neuronio.minipar": (
        (["1", "0", "0.01"], "neuron", ("1", 0)),
        (["0.5", "1", "0.1"], "neuron", ("0.5", 1)),
    ),
    "teste4_rede_neural_xor.minipar": (
        (["0", "1", "20000", "0.5"], "xor", 1),
        (["1", "1", "20000", "0.5"], "xor", 0),
    ),
    "teste5_recomendacao.minipar": (
        (HISTORY, "recommendation", True),
        (["1"] * 16, "recommendation", False),
    ),
    "teste6_quicksort_classes.minipar": (
        (["10 -3 -40 80 70 -100"], "quicksort", [-100, -40, -3, 10, 70, 80]),
        (["9 1 5 1"], "quicksort", [1, 1, 5, 9]),
        ([""], "quicksort", []),
    ),
    "teste7_quicksort_iterativo_tac.minipar": (
        (["33 12 98 5 61"], "quicksort", [5, 12, 33, 61, 98]),
        (["9 -1 9 2"], "quicksort", [-1, 2, 9, 9]),
    ),
    "teste_adicional1_paralelismo_3_computadores.minipar": (
        (["33 12 98 5 61", "1 2", "3 4", "5 6", "7 8", "5"], "three_computers",
         ([5, 12, 33, 61, 98], [[19, 22], [43, 50]], 120)),
        (["9 -1 2", "2 0", "0 2", "1 2", "3 4", "4"], "three_computers",
         ([-1, 2, 9], [[2, 4], [6, 8]], 24)),
    ),
    "teste_adicional2_tapete_sierpinski.minipar": (
        (["3"], "carpet", (3, 8)),
        (["9"], "carpet", (9, 64)),
    ),
    "teste_ascii_art_divertidapkrl.minipar": (
        (["4"], "ascii", (4, 9)),
        (["8"], "ascii", (8, 27)),
    ),
    "teste_bnf_controles_input.minipar": (
        (["Ana", "5", "2"], "controls", ("Ana", 7, 2)),
        (["Bia", "7", "3"], "controls", ("Bia", 18, 3)),
    ),
}


@unittest.skipUnless(shutil.which("g++"), "Requires g++ on PATH")
class InteractiveExampleTests(unittest.TestCase):
    def isolated_channel_source(self, source):
        # The example files keep their documented ports. Test copies use free
        # loopback ports so they cannot connect to a user's running examples.
        pattern = r'(c_channel\(\s*"127\.0\.0\.1"\s*,\s*)(\d+)(\s*\))'
        ports = list(dict.fromkeys(int(match.group(2)) for match in re.finditer(pattern, source)))
        self.assertTrue(ports, "The channel example has no loopback ports to isolate")
        replacements = {}
        with ExitStack() as reservations:
            # Keep all reservations open until the whole distinct set is known.
            for port in ports:
                reserved = reservations.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
                reserved.bind(("127.0.0.1", 0))
                replacements[port] = reserved.getsockname()[1]
            changed = re.sub(pattern, lambda match: match.group(1)
                             + str(replacements[int(match.group(2))]) + match.group(3), source)
        return changed

    def check_result(self, kind, expected, output):
        compact = re.sub(r"\s+", " ", output)
        if kind == "calculator":
            self.assertRegex(output, rf"Resultado:\s+{expected}(?:\.0+)?(?:\s|$)")
        elif kind == "factorial_fibonacci":
            factorial, fibonacci = expected
            self.assertRegex(compact, rf"Fatorial de \d+ = {factorial}(?:\s|$)")
            actual = [int(line.strip()) for line in output.splitlines() if line.strip().isdigit()]
            self.assertEqual(actual, fibonacci)
        elif kind == "neuron":
            value, desired = expected
            self.assertIn(f"Entrada: {value} Saida desejada: {desired}", compact)
            self.assertIn("Neuronio aprendeu dinamicamente.", output)
            self.assertIn(f"Valor desejado: {desired}", compact)
        elif kind == "xor":
            self.assertIn(f"Classe prevista: {expected} XOR esperado: {expected}", compact)
        elif kind == "recommendation":
            recommendations = output.split("Produtos recomendados para voce:")[-1].strip()
            if expected:
                self.assertIn("probabilidade:", recommendations)
                self.assertIn("Laptop", recommendations)
            else:
                self.assertEqual(recommendations, "")
        elif kind == "quicksort":
            formatted = "[" + ", ".join(map(str, expected)) + "]"
            # Both original class-based and iterative programs identify their
            # sorted vector; the final occurrence cannot be an input prompt.
            self.assertIn(formatted, output.split("ordenado:")[-1])
        elif kind == "three_computers":
            vector, matrix, factorial = expected
            vector_text = "[" + ", ".join(map(str, vector)) + "]"
            matrix_text = "[" + ", ".join("[" + ", ".join(map(str, row)) + "]" for row in matrix) + "]"
            self.assertIn(vector_text, output)
            self.assertIn(matrix_text, output)
            self.assertRegex(compact, rf"Fatorial[^\n]*\b{factorial}(?:\.0+)?(?:\s|$)")
        elif kind in ("carpet", "ascii"):
            size, cells = expected
            # input() prints its prompt without a newline. The first rendered
            # row can therefore follow that prompt on the same output line.
            rows = re.findall(r"\[[^\r\n]*\]", output)
            self.assertEqual(len(rows), size, output)
            self.assertEqual(sum(line.count("#" if kind == "carpet" else "A") for line in rows), cells)
        elif kind == "controls":
            name, total, attempts = expected
            self.assertIn(name, output)
            self.assertIn(f"Controle OK: {total} {attempts}", compact)
        else:
            self.fail(f"Missing result checker for {kind}")

    def check_example(self, filename):
        (ROOT / "output").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="interactive-examples-") as temporary:
            variants = CASES[filename]
            source = ROOT / "tests" / filename
            metadata = get_program_spec(str(source))
            self.assertTrue(metadata["requires_input"], filename)
            self.assertEqual(metadata["input_count"], len(variants[0][0]), filename)
            directory = Path(temporary) / source.stem
            compile_source = source
            if filename in ("teste1_calculadora_cliente_servidor.minipar",
                            "teste_adicional1_paralelismo_3_computadores.minipar"):
                compile_source = Path(temporary) / filename
                compile_source.write_text(self.isolated_channel_source(source.read_text(encoding="utf-8")),
                                          encoding="utf-8")
            compiled = subprocess.run([
                sys.executable, "-X", "utf8", "-B", str(ROOT / "main.py"),
                str(compile_source), source.stem, "--output-dir", str(directory),
            ], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=35)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            outputs = []
            for inputs, kind, expected in variants:
                with self.subTest(example=filename, inputs=inputs):
                    executed = subprocess.run(
                        [executable_path(str(directory), source.stem)],
                        input="\n".join(inputs) + "\n", cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8", timeout=15,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
                    self.assertEqual(executed.stderr, "", executed.stderr)
                    self.check_result(kind, expected, executed.stdout)
                    outputs.append(executed.stdout)
            self.assertGreaterEqual(len(outputs), 2)
            self.assertNotEqual(outputs[0], outputs[1],
                                "Changing keyboard data did not change the computed output")


def example_test(filename):
    def run(self):
        self.check_example(filename)
    return run


for example_filename in CASES:
    setattr(InteractiveExampleTests, "test_" + Path(example_filename).stem + "_uses_keyboard_data",
            example_test(example_filename))


class InteractiveTACRegressionTests(unittest.TestCase):
    def test_every_selectable_example_has_two_keyboard_input_profiles(self):
        self.assertEqual({path.name for path in (ROOT / "tests").glob("*.minipar")}, set(CASES),
                         "Every selectable example must have keyboard-input integration coverage")

    def test_iterative_quicksort_tac_is_generated_from_the_current_program(self):
        source = (ROOT / "tests/teste7_quicksort_iterativo_tac.minipar").read_text(encoding="utf-8")
        result = analysis.analyze(source, "tac")
        self.assertTrue(result["success"], result)
        self.assertIn("input", result["result"].lower())
        self.assertIn("func quicksort_iterativo:", result["result"])
        changed = source.replace("seq {", 'seq { print("CURRENT_INTERACTIVE_TAC");', 1)
        updated = analysis.analyze(changed, "tac")
        self.assertTrue(updated["success"], updated)
        self.assertIn("CURRENT_INTERACTIVE_TAC", updated["result"])
        self.assertNotEqual(result["result"], updated["result"])


if __name__ == "__main__":
    unittest.main()
