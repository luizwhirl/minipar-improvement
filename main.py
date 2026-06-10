import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from codegen import CppCodeGenerator


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python main.py <arquivo_fonte.minipar> [nome_saida]")
        return 1

    source_path  = sys.argv[1]
    output_name  = sys.argv[2] if len(sys.argv) > 2 else "programa_compilado"

    print("=== Compilador MiniPar 2026.1 (Python Version) ===")

    # 1. Leitura do arquivo fonte
    try:
        with open(source_path, encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"[ERRO] Arquivo nao encontrado: {source_path}", file=sys.stderr)
        return 1

    # 2. Análise Léxica e Sintática
    print("[Fase 1] Analise Lexica e Sintatica...")
    lexer  = Lexer(source_code)
    tokens = lexer.tokenize()

    parser  = Parser(tokens)
    program = parser.parse()

    # 3. Análise Semântica
    print("[Fase 2] Analise Semantica e Tabela de Simbolos...")
    semantic = SemanticAnalyzer()
    if not semantic.analyze(program):
        print("[ERRO] Falha na Analise Semantica. Compilacao abortada.", file=sys.stderr)
        return 1

    # 4. Geração de Código C++ e chamada do GCC
    print("[Fase 3] Transpilacao e Chamada do GCC (-O3)...")
    codegen = CppCodeGenerator()
    codegen.generate(program, output_name)

    print("=== Processo Finalizado ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())