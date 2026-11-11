"""MINIP-32: confere o Teste 11 (minicompilador de expressoes que gera Assembly ARMv7)."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from run_artifacts import executable_path
from test_interactive_examples import arm_block, run_stack_arm

FONTE = ROOT / "tests" / "teste11_minicompilador_expressoes_arm.minipar"
ESPERADO = ROOT / "tests" / "expected_results" / "teste11_minicompilador_expressoes_arm"


@unittest.skipIf(shutil.which("g++") is None, "g++ nao encontrado")
class Teste11ArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "output").mkdir(exist_ok=True)
        cls.pasta = tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="teste11-arm-")
        compilado = subprocess.run([
            sys.executable, "-X", "utf8", "-B", str(ROOT / "main.py"),
            str(FONTE), FONTE.stem, "--output-dir", cls.pasta.name,
        ], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if compilado.returncode != 0:
            cls.pasta.cleanup()
            raise AssertionError(compilado.stdout + compilado.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.pasta.cleanup()

    def rodar(self, expressao):
        executado = subprocess.run([executable_path(self.pasta.name, FONTE.stem)],
                                   input=expressao + "\n", cwd=ROOT, capture_output=True,
                                   text=True, encoding="utf-8", timeout=15)
        self.assertEqual(executado.returncode, 0, executado.stderr)
        return executado.stdout

    def test_saida_completa_bate_com_o_esperado(self):
        saida = self.rodar("2 + 3 * (4 - 1)")
        esperado = (ESPERADO.parent / (ESPERADO.name + ".expected.txt")).read_text(encoding="utf-8")
        self.assertEqual(saida.strip(), esperado.strip())

    def test_bloco_arm_bate_com_o_arquivo_arm(self):
        saida = self.rodar("2 + 3 * (4 - 1)")
        esperado = (ESPERADO.parent / (ESPERADO.name + ".expected.arm")).read_text(encoding="utf-8")
        self.assertEqual(arm_block(saida).strip(), esperado.strip())

    def test_precedencia_parenteses_divisao_e_menos_unario(self):
        casos = {
            "1 + 2 * 3": 7,
            "(1 + 2) * 3": 9,
            "10 - 4 - 3": 3,
            "100 / 7 / 2": 7,
            "-7 / 2": -3,
            "-(7 - 10) * -2 - 50 / 6": -14,
            "2147483647": 2147483647,
        }
        for expressao, valor in casos.items():
            with self.subTest(expressao=expressao):
                saida = self.rodar(expressao)
                self.assertIn(f"Resultado esperado: {valor}", saida)
                self.assertEqual(run_stack_arm(arm_block(saida)), valor)

    def test_divisao_so_inclui_a_rotina_quando_precisa(self):
        self.assertNotIn("dividir:", arm_block(self.rodar("2 * 3")))
        self.assertIn("dividir:", arm_block(self.rodar("6 / 3")))

    def test_erros_nao_geram_assembly(self):
        casos = {
            "3 $ 4": "Erro lexico: caractere invalido na posicao 3.",
            "2 +": "Erro sintatico",
            "((1)": "Erro sintatico",
            "2 3": "Erro sintatico",
            "": "Erro sintatico: expressao vazia.",
            "1 / (2 - 2)": "Erro semantico: divisao por zero.",
            "65536 * 65536": "Erro semantico: o valor passa dos 32 bits do ARM.",
            "2147483648": "Erro lexico",
        }
        for expressao, mensagem in casos.items():
            with self.subTest(expressao=expressao):
                saida = self.rodar(expressao)
                self.assertIn(mensagem, saida)
                self.assertNotIn("=== INICIO ARM ===", saida)


if __name__ == "__main__":
    unittest.main()
