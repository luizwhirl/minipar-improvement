"""MINIP-28: confere to_string, substr, s[i] e s = s + "*" (semantica e C++ gerado)."""
from contextlib import redirect_stderr
from io import StringIO
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


def analisar(code):
    """Roda a semantica e devolve (ok, mensagens de erro)."""
    program = Parser(Lexer(code).tokenize()).parse()
    erros = StringIO()
    with redirect_stderr(erros):
        ok = SemanticAnalyzer().analyze(program)
    return ok, erros.getvalue()


class SemanticaFuncoesTextoTests(unittest.TestCase):
    def test_funcoes_de_texto_sao_conhecidas(self):
        ok, erros = analisar('seq { var s = to_string(1) + substr("abc", 0, 1) + "x"[0]; print(s); }')
        self.assertTrue(ok, erros)

    def test_substr_com_argumentos_errados(self):
        ok, erros = analisar('seq { print(substr("abc", 1)); }')
        self.assertFalse(ok)
        self.assertIn("'substr' espera 3 argumento(s), recebeu 2", erros)

    def test_to_string_com_argumentos_errados(self):
        ok, erros = analisar("seq { print(to_string(1, 2)); }")
        self.assertFalse(ok)
        self.assertIn("'to_string' espera 1 argumento(s), recebeu 2", erros)

    def test_nao_altera_caractere_de_texto(self):
        ok, erros = analisar('seq { var s = "abc"; s[0] = "x"; }')
        self.assertFalse(ok)
        self.assertIn("alterar um caractere de texto", erros)

    def test_lista_continua_aceitando_atribuicao_por_indice(self):
        ok, erros = analisar("seq { var xs = [1, 2]; xs[0] = 5; print(xs); }")
        self.assertTrue(ok, erros)


@unittest.skipIf(shutil.which("g++") is None, "g++ nao encontrado")
class CppFuncoesTextoTests(unittest.TestCase):
    def compilar_e_rodar(self, code):
        ok, erros = analisar(code)
        self.assertTrue(ok, erros)
        program = Parser(Lexer(code).tokenize()).parse()
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
            return subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=30)

    def test_concatenar_no_proprio_texto(self):
        run = self.compilar_e_rodar('seq { var s = "ab"; s = s + "*"; s = s + "*"; print(s); }')
        self.assertEqual(run.stdout.strip(), "ab**")

    def test_to_string_igual_ao_print(self):
        run = self.compilar_e_rodar('seq { print("n=" + to_string(42) + " m=" + to_string(2.5)); }')
        self.assertEqual(run.stdout.strip(), "n=42 m=2.5")

    def test_substr_corta_no_fim(self):
        run = self.compilar_e_rodar('seq { print(substr("compilador", 0, 4), substr("compilador", 7, 100)); }')
        self.assertEqual(run.stdout.split(), ["comp", "dor"])

    def test_indice_em_texto_compara_com_letra(self):
        run = self.compilar_e_rodar('seq { var s = "abc"; if (s[1] == "b") { print("ok", s[2]); } }')
        self.assertEqual(run.stdout.split(), ["ok", "c"])

    def test_len_menos_um_desce_ate_zero(self):
        code = 'seq { var p = "abc"; var r = ""; var i = len(p) - 1; while (i >= 0) { r = r + p[i]; i = i - 1; } print(r); }'
        self.assertEqual(self.compilar_e_rodar(code).stdout.strip(), "cba")

    def test_indice_fora_do_texto_da_erro_de_execucao(self):
        run = self.compilar_e_rodar('seq { var s = "abc"; print(s[5]); }')
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("indice fora do texto", run.stderr)

    def test_programa_de_exemplo_bate_com_o_esperado(self):
        code = (ROOT / "tests" / "teste_funcoes_texto.minipar").read_text(encoding="utf-8")
        esperado = (ROOT / "tests" / "expected_results" / "teste_funcoes_texto.expected.txt").read_text(encoding="utf-8")
        self.assertEqual(self.compilar_e_rodar(code).stdout.strip(), esperado.strip())


if __name__ == "__main__":
    unittest.main()
