"""Compila e executa programas com fork/join para conferir o C++ gerado de verdade."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codegen import CppCodeGenerator
from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer


@unittest.skipIf(shutil.which("g++") is None, "g++ nao encontrado")
class CppForkJoinRunTests(unittest.TestCase):
    def compile_and_run(self, code):
        program = Parser(Lexer(code).tokenize()).parse()
        self.assertTrue(SemanticAnalyzer().analyze(program))
        cpp = CppCodeGenerator().generate_text(program)
        with tempfile.TemporaryDirectory() as tmp:
            cpp_path = Path(tmp) / "programa.cpp"
            exe_path = Path(tmp) / ("programa.exe" if sys.platform == "win32" else "programa")
            cpp_path.write_text(cpp, encoding="utf-8")
            command = ["g++", "-std=c++20", "-O1", str(cpp_path), "-o", str(exe_path), "-pthread"]
            if sys.platform == "win32":
                command.append("-lws2_32")
            build = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            return run.stdout.split()

    def test_join_guardado_em_variavel_na_recursao(self):
        code = """
func fib(n) {
    if (n <= 1) { return n; }
    var t1 = fork fib(n - 1);
    var t2 = fork fib(n - 2);
    var a = join(t1);
    var b = join(t2);
    return a + b;
}
seq { print(fib(5)); }
"""
        self.assertEqual(self.compile_and_run(code), ["5"])

    def test_fork_de_metodo_que_altera_a_lista(self):
        code = """
func identity(x) { return x; }
seq {
    var xs = [41, 42];
    var t = fork xs.pop();
    print(join(t));
    var ys = [7, 8];
    var u = fork identity(ys.pop());
    print(join(u));
}
"""
        self.assertEqual(self.compile_and_run(code), ["42", "8"])

    def test_lista_de_tarefas_em_laco(self):
        code = """
func dobro(i) { return i * 2; }
seq {
    var tarefas = [];
    for (var i in range(4)) { tarefas.append(fork dobro(i)); }
    var total = 0;
    for (var t in tarefas) { total = total + join(t); }
    print(total);
}
"""
        self.assertEqual(self.compile_and_run(code), ["12"])


if __name__ == "__main__":
    unittest.main()
