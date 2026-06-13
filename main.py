import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from tac import TACGenerator
from codegen import CppCodeGenerator

def compile_file(source_path: str, output_name: str) -> bool:
    """Processa as 3 Fases do Compilador em um arquivo alvo."""
    print(f"\n=== Compilando: {source_path} ===")
    try:
        with open(source_path, encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"[ERRO] Arquivo nao encontrado: {source_path}", file=sys.stderr)
        return False

    print("[Fase 1] Analise Lexica e Sintatica...")
    lexer  = Lexer(source_code)
    tokens = lexer.tokenize()

    parser  = Parser(tokens)
    program = parser.parse()

    print("[Fase 2] Analise Semantica e Tabela de Simbolos...")
    semantic = SemanticAnalyzer()
    if not semantic.analyze(program):
        print("[ERRO] Falha na Analise Semantica. Compilacao abortada.", file=sys.stderr)
        return False

    print("[Fase 3] Geracao de Codigo Intermediario (TAC - 3 enderecos)...")
    tac = TACGenerator()
    tac_path = tac.generate(program, output_name)
    print(f"[TAC] Arquivo gerado: {tac_path}")

    print("[Fase 4] Transpilacao e Chamada do GCC (-O3)...")
    codegen = CppCodeGenerator()
    return codegen.generate(program, output_name)

def main() -> int:
    # Se rodar sem argumentos (ex: `python main.py`), inicia o menu interativo
    if len(sys.argv) < 2:
        try:
            import menu
            menu.exibir_menu()
            return 0
        except ImportError:
            print("Uso: python main.py <arquivo_fonte.minipar> [nome_saida]")
            return 1

    # Caso passe os parametros diretamente via CLI
    source_path  = sys.argv[1]
    output_name  = sys.argv[2] if len(sys.argv) > 2 else "programa_compilado"

    print("=== Compilador MiniPar 2026.1 (Python Version) ===")
    success = compile_file(source_path, output_name)
    
    if success:
        print("=== Processo Finalizado ===")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
