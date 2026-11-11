"""MINIP-30: fork f(x) on canal e join(t, ms).

Neste passo o fork com "on" ainda roda neste computador; a rede entra no passo 3.
"""
import contextlib
import io
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codegen import CppCodeGenerator
from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from tac import TACGenerator


def parse(code):
    return Parser(Lexer(code).tokenize()).parse()


def analisar(code):
    """Roda a semantica e devolve (passou, texto dos erros)."""
    erros = io.StringIO()
    with contextlib.redirect_stderr(erros):
        ok = SemanticAnalyzer().analyze(parse(code))
    return ok, erros.getvalue()


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PROGRAMA = """
func quadrado(x) { return x * x; }
func soma(a, b) { return a + b; }
var canal = c_channel("127.0.0.1", PORTA);
var t1 = fork quadrado(5);
var t2 = fork quadrado(7) on canal;
var t3 = fork soma(2.5, 4) on canal;
print(join(t1));
print(join(t2, 5000));
print(join(t3));
"""


class SintaxeESemanticaTests(unittest.TestCase):
    def test_fork_on_e_join_com_tempo_sao_aceitos(self):
        ok, erros = analisar(PROGRAMA.replace("PORTA", "7000"))
        self.assertTrue(ok, erros)

    def test_destino_que_nao_e_canal_tem_codigo_sem_fj_03(self):
        ok, erros = analisar('func f(x) { return x; }\nvar t = fork f(1) on "127.0.0.1:7000";\n')
        self.assertFalse(ok)
        self.assertIn("[SEM_FJ_03] Linha 2", erros)

    def test_tempo_que_nao_e_numero_tem_codigo_sem_fj_04(self):
        ok, erros = analisar('func f(x) { return x; }\nvar t = fork f(1);\nvar r = join(t, "muito");\n')
        self.assertFalse(ok)
        self.assertIn("[SEM_FJ_04] Linha 3", erros)

    def test_fork_remoto_de_metodo_ou_funcao_pronta_tem_codigo_sem_fj_05(self):
        code = ('var c = c_channel("127.0.0.1", 7000);\n'
                'var xs = [1, 2];\n'
                'var t = fork len(xs) on c;\n')
        ok, erros = analisar(code)
        self.assertFalse(ok)
        self.assertIn("[SEM_FJ_05] Linha 3", erros)

    def test_fork_remoto_com_texto_tem_codigo_sem_fj_06(self):
        code = ('func f(x) { return 1; }\n'
                'var c = c_channel("127.0.0.1", 7000);\n'
                'var t = fork f("oi") on c;\n')
        ok, erros = analisar(code)
        self.assertFalse(ok)
        self.assertIn("[SEM_FJ_06] Linha 3", erros)

    def test_tac_mostra_destino_e_tempo(self):
        tac = TACGenerator().generate_text(parse(PROGRAMA.replace("PORTA", "7000")))
        self.assertIn("spawn quadrado, 1 on canal", tac)
        self.assertRegex(tac, r"= join t\d+, 5000")



@unittest.skipIf(shutil.which("g++") is None, "g++ nao encontrado")
class ExecucaoDistribuidaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workers = []
        self.addCleanup(self.parar_workers)

    def parar_workers(self):
        for w in self.workers:
            if w.poll() is None:
                w.kill()
                w.communicate()

    def compilar(self, code, nome):
        cpp = CppCodeGenerator().generate_text(parse(code))
        cpp_path = Path(self.tmp.name) / f"{nome}.cpp"
        exe_path = Path(self.tmp.name) / (f"{nome}.exe" if sys.platform == "win32" else nome)
        cpp_path.write_text(cpp, encoding="utf-8")
        command = ["g++", "-std=c++20", "-O1", str(cpp_path), "-o", str(exe_path), "-pthread"]
        if sys.platform == "win32":
            command.append("-lws2_32")
        compiled = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        return str(exe_path)

    def iniciar_worker(self, exe, porta):
        w = subprocess.Popen([exe, "--worker", str(porta)], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        self.workers.append(w)
        self.assertIn("Esperando tarefas", w.stdout.readline())
        return w

    def test_fork_on_ainda_roda_neste_computador(self):
        exe = self.compilar(PROGRAMA.replace("PORTA", "7000"), "programa")
        run = subprocess.run([exe], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.split(), ["25", "49", "6.5"])

    def test_join_com_tempo_para_o_programa_quando_passa_do_limite(self):
        code = ("func demora(n) { var s = 0; var i = 0; while (i < n) { s = s + i; i = i + 1; } return s; }\n"
                "var t = fork demora(4000000000);\n"
                "print(join(t, 50));\n")
        exe = self.compilar(code, "demora")
        inicio = time.monotonic()
        run = subprocess.run([exe], capture_output=True, text=True, timeout=30)
        self.assertLess(time.monotonic() - inicio, 10)
        self.assertEqual(run.returncode, 1)
        self.assertIn("passou do tempo limite de 50 ms", run.stderr)



if __name__ == "__main__":
    unittest.main()
