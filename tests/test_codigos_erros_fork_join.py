"""MINIP-30 (passo 1): os erros semanticos de fork/join saem com codigo SEM_FJ_xx."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer


def analisar(code):
    """Roda a semantica e devolve (passou, texto dos erros)."""
    program = Parser(Lexer(code).tokenize()).parse()
    erros = io.StringIO()
    with contextlib.redirect_stderr(erros):
        ok = SemanticAnalyzer().analyze(program)
    return ok, erros.getvalue()


class CodigosErrosForkJoinTests(unittest.TestCase):
    def test_fork_sem_chamada_tem_codigo_sem_fj_01(self):
        ok, erros = analisar("var t = fork 5;\n")
        self.assertFalse(ok)
        self.assertIn("[SEM_FJ_01] Linha 1", erros)

    def test_join_sem_tarefa_tem_codigo_sem_fj_02(self):
        ok, erros = analisar('var a = join("texto");\n')
        self.assertFalse(ok)
        self.assertIn("[SEM_FJ_02] Linha 1", erros)

    def test_fork_join_corretos_nao_geram_erro(self):
        code = "func dobro(x) { return x * 2; }\nvar t = fork dobro(3);\nvar r = join(t);\nprint(r);\n"
        ok, erros = analisar(code)
        self.assertTrue(ok, erros)
        self.assertNotIn("SEM_FJ", erros)

    def test_outros_erros_continuam_sem_codigo(self):
        ok, erros = analisar("print(x);\n")
        self.assertFalse(ok)
        self.assertIn("[ERRO SEMANTICO] Linha 1", erros)
        self.assertNotIn("SEM_FJ", erros)


if __name__ == "__main__":
    unittest.main()
