"""MINIP-20: Bateria de testes de regressao do MiniPar 2026.1.

Garante que todos os 11 programas de teste do MiniPar 2026.1 (7 obrigatorios
e 4 adicionais), a gramatica/semantica OO de 2026.1, o gerador TAC, o gerador
C++ e as interfaces Web Legacy (/legacy) e CLI (main.py / menu.py) continuam
funcionando sem regressao no MiniPar 2026.2.
"""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import analysis_worker as analysis
import app as web
import main as cli_main
import menu
from ast_nodes import (
    Assignment,
    BinaryExpr,
    BreakStmt,
    CChannelExpr,
    ClassDecl,
    ContinueStmt,
    DoWhileStmt,
    ForStmt,
    FuncCallExpr,
    FuncDecl,
    IfStmt,
    IndexAssign,
    IndexExpr,
    InputExpr,
    ListLiteral,
    MatrixCreateExpr,
    MethodCall,
    NewExpr,
    ParBlock,
    PrintStmt,
    Program,
    PropertyAccess,
    PropertyAssign,
    ReceiveExpr,
    ReturnStmt,
    SendStmt,
    SeqBlock,
    ThisExpr,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from codegen import CppCodeGenerator
from lexer import Lexer, TokenType
from parser import Parser
from program_analyzer import get_program_spec
from run_artifacts import executable_path
from semantic import SemanticAnalyzer
from tac import TACGenerator


# Os 11 programas de teste do MiniPar 2026.1 (7 obrigatorios + 4 adicionais)
# com seus metadados esperados de entradas e canais.
MINIPAR_2026_1_SPECS = {
    "teste1_calculadora_cliente_servidor.minipar": {
        "requires_input": True,
        "input_count": 3,
        "channel_count": 2,
        "multi_computer_count": 2,
        "ast_nodes": (CChannelExpr, SendStmt, ReceiveExpr, ParBlock, SeqBlock, IfStmt),
        "cpp_snippets": ("MiniParChannel", "sendData", "receiveData", "std::vector<std::thread>"),
        "tac_snippets": ("c_channel(", "send ", "receive "),
    },
    "teste2_fatorial_fibonacci_par.minipar": {
        "requires_input": True,
        "input_count": 2,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (FuncDecl, ParBlock, SeqBlock, WhileStmt, MethodCall, IndexExpr),
        "cpp_snippets": ("std::vector<std::thread>", "__m_thr.emplace_back", ".push_back(", "__index("),
        "tac_snippets": ("func inteiro_no_intervalo:", "WHILE_", "ENDWHILE_"),
    },
    "teste3_neuronio.minipar": {
        "requires_input": True,
        "input_count": 3,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (ClassDecl, FuncDecl, ThisExpr, PropertyAccess, PropertyAssign, NewExpr, WhileStmt),
        "cpp_snippets": ("class Neuronio", "std::make_shared<Neuronio>()", "this->peso", "this->ativacao(", "neuronio->treinar()"),
        "tac_snippets": ("# class Neuronio", "func ativacao:", "func treinar:", "new Neuronio"),
    },
    "teste4_rede_neural_xor.minipar": {
        "requires_input": True,
        "input_count": 4,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (FuncDecl, ClassDecl, WhileStmt, NewExpr, PropertyAssign, MethodCall),
        "cpp_snippets": (
            "class RedeNeuralXOR",
            "std::make_shared<RedeNeuralXOR>()",
            "std::exp(",
            "derivada_sigmoid(",
            "this->feedforward(",
        ),
        "tac_snippets": ("func sigmoid:", "func derivada_sigmoid:", "# class RedeNeuralXOR", "func feedforward:"),
    },
    "teste5_recomendacao.minipar": {
        "requires_input": True,
        "input_count": 16,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (ClassDecl, FuncDecl, ListLiteral, IndexExpr, IndexAssign, WhileStmt),
        "cpp_snippets": (
            "class RedeNeuralRecomendacao",
            "class Recomendador",
            "std::make_shared<RedeNeuralRecomendacao>()",
            "std::make_shared<Recomendador>()",
            "std::exp(",
        ),
        "tac_snippets": (
            "func relu:",
            "func sigmoid:",
            "# class RedeNeuralRecomendacao",
            "# class Recomendador",
            "func forward:",
            "func recomendar:",
        ),
    },
    "teste6_quicksort_classes.minipar": {
        "requires_input": True,
        "input_count": 1,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (ClassDecl, MethodCall, IndexAssign, WhileStmt, IfStmt),
        "cpp_snippets": ("class Quicksort", "this->quicksort(", "this->particionar(", "__parse_ints("),
        "tac_snippets": ("# class Quicksort", "func particionar:", "func quicksort:", "func ordenar:"),
    },
    "teste7_quicksort_iterativo_tac.minipar": {
        "requires_input": True,
        "input_count": 1,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (FuncDecl, WhileStmt, ContinueStmt, MethodCall, IndexAssign),
        "cpp_snippets": ("quicksort_iterativo(", "__array_pop(", ".push_back(", "continue;"),
        "tac_snippets": ("func quicksort_iterativo:", "endfunc quicksort_iterativo", "ifFalse ", "goto "),
    },
    "teste_adicional1_paralelismo_3_computadores.minipar": {
        "requires_input": True,
        "input_count": 6,
        "channel_count": 3,
        "multi_computer_count": 3,
        "ast_nodes": (CChannelExpr, ParBlock, SendStmt, ReceiveExpr, MatrixCreateExpr),
        "cpp_snippets": ("MiniParChannel", "std::vector<std::thread>", "__make_matrix("),
        "tac_snippets": ("c_channel(", "send ", "receive "),
    },
    "teste_adicional2_tapete_sierpinski.minipar": {
        "requires_input": True,
        "input_count": 1,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (FuncDecl, MatrixCreateExpr, IndexAssign, WhileStmt, IfStmt),
        "cpp_snippets": ("preencher(", "__make_matrix(", "__index(__index(tela,"),
        "tac_snippets": ("func preencher:", "endfunc preencher", "matrix("),
    },
    "teste_ascii_art_divertidapkrl.minipar": {
        "requires_input": True,
        "input_count": 1,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (MatrixCreateExpr, IndexAssign, IndexExpr, WhileStmt, IfStmt),
        "cpp_snippets": ("__make_matrix(", "__index(__index(controle,", "__index(__index(tela,"),
        "tac_snippets": ("matrix(", "WHILE_", "ENDWHILE_"),
    },
    "teste_bnf_controles_input.minipar": {
        "requires_input": True,
        "input_count": 3,
        "channel_count": 0,
        "multi_computer_count": None,
        "ast_nodes": (FuncDecl, ForStmt, ContinueStmt, DoWhileStmt, BreakStmt, InputExpr),
        "cpp_snippets": ("for (auto i = 0;", "continue;", "do\n", "break;", "input("),
        "tac_snippets": ("FOR_", "FOR_STEP_", "ENDFOR_", "DO_", "ENDDO_"),
    },
}

# Resultados de referencia do MiniPar 2026.1 mantidos em tests/expected_results/.
EXPECTED_2026_1_FIXTURES = (
    "teste3_neuronio.expected.txt",
    "teste4_rede_neural_xor.expected.txt",
    "teste5_recomendacao.expected.txt",
    "teste6_quicksort_classes.expected.txt",
    "teste7_quicksort_iterativo_tac.expected.tac",
    "teste7_quicksort_iterativo_tac.expected.txt",
)


def _walk_ast(node):
    """Percorre recursivamente todos os nos da AST."""
    if node is None:
        return
    yield node
    if isinstance(node, list):
        for item in node:
            yield from _walk_ast(item)
        return
    if hasattr(node, "__dataclass_fields__"):
        for field_name in node.__dataclass_fields__:
            value = getattr(node, field_name)
            if isinstance(value, list):
                for item in value:
                    if hasattr(item, "__dataclass_fields__"):
                        yield from _walk_ast(item)
            elif hasattr(value, "__dataclass_fields__"):
                yield from _walk_ast(value)


def _compile_pipeline(source_code: str):
    """Executa Lexer -> Parser -> SemanticAnalyzer -> TACGenerator -> CppCodeGenerator."""
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    program = Parser(tokens).parse()
    stderr_buffer = StringIO()
    with redirect_stderr(stderr_buffer):
        semantic_ok = SemanticAnalyzer().analyze(program)
    tac_text = TACGenerator().generate_text(program)
    cpp_text = CppCodeGenerator().generate_text(program)
    return {
        "lexer": lexer,
        "tokens": tokens,
        "program": program,
        "semantic_ok": semantic_ok,
        "semantic_errors": stderr_buffer.getvalue(),
        "tac": tac_text,
        "cpp": cpp_text,
    }


def _has_working_cpp20_gpp() -> bool:
    """Verifica se ha um g++ funcional no ambiente com suporte a -std=c++20."""
    if shutil.which("g++") is None:
        return False
    try:
        probe = subprocess.run(
            ["g++", "-std=c++20", "-x", "c++", "-", "-fsyntax-only"],
            input="int main() { return 0; }\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        return probe.returncode == 0
    except OSError:
        return False


class Minipar20261CatalogAndPhasesTests(unittest.TestCase):
    """Garante que os 11 testes do MiniPar 2026.1 passam por todas as fases do compilador."""

    def test_todos_os_11_arquivos_do_minipar_2026_1_existem_e_tem_fixtures_preservadas(self):
        for filename in MINIPAR_2026_1_SPECS:
            with self.subTest(filename=filename):
                path = ROOT / "tests" / filename
                self.assertTrue(path.is_file(), f"Arquivo ausente: {path}")
                self.assertTrue(path.read_text(encoding="utf-8").strip())

        for fixture in EXPECTED_2026_1_FIXTURES:
            with self.subTest(fixture=fixture):
                fixture_path = ROOT / "tests" / "expected_results" / fixture
                self.assertTrue(fixture_path.is_file(), f"Fixture de 2026.1 ausente: {fixture_path}")
                self.assertTrue(fixture_path.read_text(encoding="utf-8").strip())

    def test_todos_os_11_programas_de_2026_1_passam_por_lexer_parser_semantica_tac_e_cpp(self):
        for filename, expected in MINIPAR_2026_1_SPECS.items():
            with self.subTest(filename=filename):
                source = (ROOT / "tests" / filename).read_text(encoding="utf-8")
                result = _compile_pipeline(source)

                self.assertFalse(result["lexer"].has_errors, result["lexer"].errors)
                self.assertEqual(result["tokens"][-1].type, TokenType.END_OF_FILE)
                self.assertIsInstance(result["program"], Program)
                self.assertTrue(result["program"].statements)
                self.assertTrue(result["semantic_ok"], result["semantic_errors"])
                self.assertEqual(result["semantic_errors"], "")

                node_types = {type(node) for node in _walk_ast(result["program"])}
                for expected_node in expected["ast_nodes"]:
                    self.assertIn(
                        expected_node,
                        node_types,
                        f"{filename} deveria conter o no {expected_node.__name__} na AST",
                    )

                for tac_snippet in expected["tac_snippets"]:
                    self.assertIn(
                        tac_snippet,
                        result["tac"],
                        f"Trecho TAC {tac_snippet!r} ausente em {filename}",
                    )

                self.assertIn("int main()", result["cpp"])
                for cpp_snippet in expected["cpp_snippets"]:
                    self.assertIn(
                        cpp_snippet,
                        result["cpp"],
                        f"Trecho C++ {cpp_snippet!r} ausente em {filename}",
                    )

    def test_worker_de_analise_processa_todas_as_5_fases_para_os_11_testes_de_2026_1(self):
        for filename in MINIPAR_2026_1_SPECS:
            source = (ROOT / "tests" / filename).read_text(encoding="utf-8")
            for phase in ("tokens", "ast", "semantic", "tac", "cpp"):
                with self.subTest(filename=filename, phase=phase):
                    data = analysis.analyze(source, phase)
                    self.assertTrue(data["success"], data)
                    self.assertEqual(data["phase"], phase)
                    self.assertIsNone(data["failed_phase"])
                    self.assertEqual(data["diagnostics"], [])
                    self.assertIsNotNone(data["result"])


class Minipar20261OriginalConstructsRegressionTests(unittest.TestCase):
    """Garante que os construtos e codigos originais do MiniPar 2026.1 nao sofreram regressao."""

    def test_Fontes_originais_fixos_do_minipar_2026_1_continuam_compilando_em_todas_as_fases(self):
        # Programas no formato exato de 2026.1 (ex.: par no topo sem seq externo,
        # classes com atributos fixos, quicksort iterativo fixo, tapete 9x9 fixo).
        original_2026_1_programs = {
            "teste2_par_no_topo": """
par {
    seq {
        var n = 5;
        var fat = 1;
        var i = 1;
        while (i <= n) {
            fat = fat * i;
            i = i + 1;
        }
        print("Fatorial de 5:", fat);
    }
    seq {
        var limite = 8;
        var a = 0;
        var b = 1;
        var i = 0;
        print("Fibonacci:");
        while (i < limite) {
            print(a);
            var prox = a + b;
            a = b;
            b = prox;
            i = i + 1;
        }
    }
}
""",
            "teste3_neuronio_fixo": """
class Neuronio {
    var input_val = 1;
    var output_desejado = 0;
    var peso = 0.5;
    var bias = 1;
    var peso_bias = 0.5;
    var taxa_aprendizado = 0.01;
    var erro = 999;
    var iteracao = 0;

    func ativacao(soma) {
        if (soma > 0) {
            return 1;
        }
        return 0;
    }

    func treinar() {
        while (this.erro != 0) {
            this.iteracao = this.iteracao + 1;
            var soma = (this.input_val * this.peso) + (this.bias * this.peso_bias);
            var saida = this.ativacao(soma);
            this.erro = this.output_desejado - saida;
            if (this.erro != 0) {
                this.peso = this.peso + (this.taxa_aprendizado * this.input_val * this.erro);
                this.peso_bias = this.peso_bias + (this.taxa_aprendizado * this.bias * this.erro);
            }
        }
        print("Valor desejado:", this.output_desejado);
    }
}
seq {
    var neuronio = new Neuronio();
    neuronio.treinar();
}
""",
            "teste7_quicksort_iterativo_fixo": """
func quicksort_iterativo(arr) {
    var stack = [0, 4];
    var sp = 2;
    while (sp > 0) {
        sp = sp - 1;
        var fim = stack.pop();
        sp = sp - 1;
        var inicio = stack.pop();
        if (inicio >= fim) {
            continue;
        }
        var pivot = arr[fim];
        var i = inicio - 1;
        var j = inicio;
        while (j < fim) {
            if (arr[j] <= pivot) {
                i = i + 1;
                var temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
            j = j + 1;
        }
        i = i + 1;
        var temp2 = arr[i];
        arr[i] = arr[fim];
        arr[fim] = temp2;
        stack.append(inicio);
        stack.append(i - 1);
        sp = sp + 2;
        stack.append(i + 1);
        stack.append(fim);
        sp = sp + 2;
    }
    return arr;
}
seq {
    var array = [33, 12, 98, 5, 61];
    var ordenado = quicksort_iterativo(array);
    print("Array ordenado:", ordenado);
}
""",
            "heranca_e_tipos_explicitos_2026_1": """
class Base {
    var base_val = 10;
    func obter_base() {
        return this.base_val;
    }
}
class Derivada extends Base {
    var extra = 5;
    func somar(int fator) {
        return this.extra * fator;
    }
}
seq {
    number a = 2.5;
    int b = 4;
    string msg = "Resultado:";
    bool ativo = true;
    list valores = [1, 2, 3];
    var obj = new Derivada();
    if (ativo && (b > 2 || a < 1.0)) {
        print(msg, obj.somar(b) + a, valores[0]);
    }
}
""",
        }

        for name, code in original_2026_1_programs.items():
            with self.subTest(program=name):
                result = _compile_pipeline(code)
                self.assertFalse(result["lexer"].has_errors, result["lexer"].errors)
                self.assertTrue(result["semantic_ok"], result["semantic_errors"])
                self.assertTrue(result["tac"].strip())
                self.assertIn("int main()", result["cpp"])

        # Confere traducao especifica de heranca (extends -> : public Base)
        heranca_cpp = _compile_pipeline(original_2026_1_programs["heranca_e_tipos_explicitos_2026_1"])["cpp"]
        self.assertIn("class Derivada : public Base", heranca_cpp)

    def test_precedencia_de_operadores_e_comentarios_de_2026_1(self):
        code = """
# Comentario inicial ignorado pelo Lexer
seq {
    # Precedencia: * / % antes de + -, comparacoes antes de &&, && antes de ||
    var r = 2 + 3 * 4 - 10 / 2;
    var ok = 1 + 2 == 3 && !false || 4 > 10;
    print(r, ok); # Comentario no fim da linha
}
"""
        result = _compile_pipeline(code)
        self.assertFalse(result["lexer"].has_errors)
        self.assertTrue(result["semantic_ok"], result["semantic_errors"])

        seq_block = result["program"].statements[0]
        var_r = seq_block.statements[0]
        self.assertIsInstance(var_r, VarDecl)
        # (2 + (3 * 4)) - (10 / 2)
        self.assertIsInstance(var_r.init_value, BinaryExpr)
        self.assertEqual(var_r.init_value.op, "-")
        self.assertEqual(var_r.init_value.left.op, "+")
        self.assertEqual(var_r.init_value.left.right.op, "*")
        self.assertEqual(var_r.init_value.right.op, "/")

        var_ok = seq_block.statements[1]
        # ((1 + 2 == 3) && (!false)) || (4 > 10)
        self.assertIsInstance(var_ok.init_value, BinaryExpr)
        self.assertEqual(var_ok.init_value.op, "||")
        self.assertEqual(var_ok.init_value.left.op, "&&")
        self.assertIsInstance(var_ok.init_value.left.right, UnaryExpr)
        self.assertEqual(var_ok.init_value.left.right.op, "!")

    def test_regras_semanticas_de_erros_do_minipar_2026_1_continuam_ativas(self):
        invalid_cases = {
            "variavel_nao_declarada": (
                "seq { print(nao_existe); }",
                "Variavel 'nao_existe' nao declarada",
            ),
            "redeclaracao_mesmo_escopo": (
                "seq { var x = 1; var x = 2; }",
                "Variavel 'x' ja declarada",
            ),
            "tipo_incompativel_declaracao": (
                'seq { int n = "texto"; }',
                "Tipo incompativel em 'n'",
            ),
            "tipo_incompativel_atribuicao": (
                'seq { int n = 10; n = "texto"; }',
                "Tipo incompativel em atribuicao de 'n'",
            ),
            "operador_aritmetico_nao_numerico": (
                'seq { var x = "a" - "b"; }',
                "Operador '-' exige operandos numericos",
            ),
            "break_fora_de_laco": (
                "seq { break; }",
                "'break' usado fora de laco",
            ),
            "continue_fora_de_laco": (
                "seq { continue; }",
                "'continue' usado fora de laco",
            ),
            "funcao_nao_declarada": (
                "seq { inexistente(1); }",
                "Funcao 'inexistente' nao declarada",
            ),
            "funcao_aridade_incorreta": (
                "func soma(a, b) { return a + b; } seq { print(soma(1)); }",
                "Funcao 'soma' espera 2 argumento(s), recebeu 1",
            ),
            "classe_nao_declarada": (
                "seq { var o = new Fantasma(); }",
                "Classe 'Fantasma' nao declarada",
            ),
            "superclasse_nao_declarada": (
                "class Filha extends SuperInexistente { var a = 1; } seq { print(1); }",
                "Superclasse 'SuperInexistente' nao declarada",
            ),
            "metodo_nao_declarado": (
                "class Caixa { var v = 1; } seq { var c = new Caixa(); c.abrir(); }",
                "Metodo 'abrir' nao declarado em 'Caixa'",
            ),
            "metodo_aridade_incorreta": (
                "class Caixa { func guardar(x) { return x; } } seq { var c = new Caixa(); c.guardar(1, 2); }",
                "Metodo 'guardar' espera 1 argumento(s), recebeu 2",
            ),
            "atributo_nao_declarado_leitura": (
                "class Caixa { var v = 1; } seq { var c = new Caixa(); print(c.outro); }",
                "Atributo 'outro' nao declarado em 'Caixa'",
            ),
            "atributo_nao_declarado_escrita": (
                "class Caixa { var v = 1; } seq { var c = new Caixa(); c.outro = 2; }",
                "Atributo 'outro' nao declarado em 'Caixa'",
            ),
        }

        for name, (code, expected_error) in invalid_cases.items():
            with self.subTest(case=name):
                result = _compile_pipeline(code)
                self.assertFalse(result["semantic_ok"], f"Deveria falhar semanticamente: {name}")
                self.assertIn(expected_error, result["semantic_errors"])


class Minipar20261InterfacesAndLegacyRegressionTests(unittest.TestCase):
    """Garante que a interface Web Legacy (2026.1) e a CLI/Menu preservam o contrato de 2026.1."""

    def setUp(self):
        self.client = web.app.test_client()

    def test_rota_legacy_e_listagem_de_todos_os_11_testes_de_2026_1(self):
        legacy_resp = self.client.get("/legacy")
        self.assertEqual(legacy_resp.status_code, 200)
        html = legacy_resp.get_data(as_text=True)
        for element_id in ("editor-minipar", "editor-cpp", "editor-tac", "btn-run", "btn-clear", "test-list", "terminal-output"):
            self.assertIn(f'id="{element_id}"', html)

        tests_resp = self.client.get("/api/tests")
        self.assertEqual(tests_resp.status_code, 200)
        available = set(tests_resp.get_json()["tests"])
        self.assertTrue(set(MINIPAR_2026_1_SPECS).issubset(available))

    def test_get_test_e_test_spec_para_todos_os_11_testes_de_2026_1(self):
        for filename, expected in MINIPAR_2026_1_SPECS.items():
            with self.subTest(filename=filename):
                get_resp = self.client.post("/api/get_test", json={"filename": filename})
                self.assertEqual(get_resp.status_code, 200)
                disk_source = (ROOT / "tests" / filename).read_text(encoding="utf-8")
                self.assertEqual(get_resp.get_json()["code"], disk_source)

                spec_resp = self.client.post("/api/test_spec", json={"filename": filename})
                self.assertEqual(spec_resp.status_code, 200)
                spec = spec_resp.get_json()
                self.assertEqual(spec["requires_input"], expected["requires_input"])
                self.assertEqual(spec["input_count"], expected["input_count"])
                self.assertEqual(spec["channel_count"], expected["channel_count"])
                if expected["multi_computer_count"] is None:
                    self.assertIsNone(spec["multi_computer"])
                else:
                    self.assertIsNotNone(spec["multi_computer"])
                    self.assertEqual(spec["multi_computer"]["count"], expected["multi_computer_count"])
                    self.assertTrue(spec["multi_computer"]["required"])

    def test_cli_compile_file_gera_tac_e_cpp_e_invoca_gpp_para_teste_de_2026_1(self):
        (ROOT / "output").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="reg-2026-1-cli-") as tmp:
            out_dir = Path(tmp) / "teste3_neuronio"
            source_path = str(ROOT / "tests" / "teste3_neuronio.minipar")

            def fake_gpp(command, *args, **kwargs):
                self.assertEqual(command[0], "g++")
                self.assertIn("-std=c++20", command)
                self.assertIn("-O3", command)
                self.assertIn("-pthread", command)
                exe_idx = command.index("-o") + 1
                Path(command[exe_idx]).write_bytes(b"FAKE_BIN")
                return subprocess.CompletedProcess(command, 0)

            with patch("codegen.subprocess.run", side_effect=fake_gpp) as mocked_run, \
                    redirect_stdout(StringIO()):
                ok = cli_main.compile_file(source_path, "teste3_neuronio", str(out_dir))

            self.assertTrue(ok)
            mocked_run.assert_called_once()
            self.assertTrue((out_dir / "teste3_neuronio.tac").is_file())
            self.assertTrue((out_dir / "teste3_neuronio.cpp").is_file())
            self.assertTrue(Path(executable_path(str(out_dir), "teste3_neuronio")).is_file())


@unittest.skipUnless(_has_working_cpp20_gpp(), "Requer g++ funcional com suporte a -std=c++20")
class Minipar20261ExecutableRegressionTests(unittest.TestCase):
    """Compila com g++ e executa programas no formato original de 2026.1 quando g++ C++20 esta disponivel."""

    def compile_and_run_source(self, source_code: str, stdin_data: str = "") -> str:
        (ROOT / "output").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "output", prefix="reg-2026-1-exec-") as tmp:
            work = Path(tmp)
            src_file = work / "programa.minipar"
            src_file.write_text(source_code, encoding="utf-8")
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "-B",
                    str(ROOT / "main.py"),
                    str(src_file),
                    "programa",
                    "--output-dir",
                    str(work),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=35,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            executed = subprocess.run(
                [executable_path(str(work), "programa")],
                input=stdin_data,
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
            return executed.stdout

    def test_quicksort_classes_de_2026_1_produz_saida_de_referencia(self):
        source = (ROOT / "tests" / "teste6_quicksort_classes.minipar").read_text(encoding="utf-8")
        output = self.compile_and_run_source(source, stdin_data="10 -3 -40 80 70 -100\n")
        self.assertIn("Vetor original: [10, -3, -40, 80, 70, -100]", output)
        self.assertIn("Vetor ordenado: [-100, -40, -3, 10, 70, 80]", output)

    def test_quicksort_iterativo_de_2026_1_produz_saida_de_referencia(self):
        source = (ROOT / "tests" / "teste7_quicksort_iterativo_tac.minipar").read_text(encoding="utf-8")
        expected = (ROOT / "tests" / "expected_results" / "teste7_quicksort_iterativo_tac.expected.txt").read_text(
            encoding="utf-8"
        ).strip()
        output = self.compile_and_run_source(source, stdin_data="33 12 98 5 61\n")
        self.assertIn(expected, output)


if __name__ == "__main__":
    unittest.main()
