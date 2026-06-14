import os
import sys
import subprocess
import glob

# Importa a função de compilação refatorada no main.py
from main import compile_file

def executar_binario(output_name: str):
    """Executa o arquivo gerado apos a compilacao."""
    exe_ext = ".exe" if sys.platform == "win32" else ""
    exe_path = os.path.join("output", f"{output_name}{exe_ext}")
    
    if os.path.exists(exe_path):
        abs_exe_path = os.path.abspath(exe_path)
        print(f"\n--- Executando {output_name} ---")
        try:
            # Roda o binário recém-criado pelo GCC
            subprocess.run([abs_exe_path])
        except Exception as e:
            print(f"[ERRO] Falha ao executar {exe_path}: {e}")
        print("-" * 40)
    else:
        print(f"[ERRO] Executavel {exe_path} nao encontrado apos compilacao.")

def obter_testes() -> list:
    """Retorna uma lista de todos os arquivos .minipar dentro da pasta tests."""
    tests_dir = "tests"
    if not os.path.exists(tests_dir):
        print(f"[ERRO] Diretorio '{tests_dir}' nao encontrado!")
        return []
    
    testes = glob.glob(os.path.join(tests_dir, "*.minipar"))
    return sorted(testes)

def rodar_todos():
    testes = obter_testes()
    if not testes:
        return

    print(f"\n=== Rodando todos os testes ({len(testes)} encontrados) ===")
    for teste in testes:
        base_name = os.path.basename(teste).replace(".minipar", "")
        success = compile_file(teste, base_name)
        if success:
            executar_binario(base_name)
        else:
            print(f"[AVISO] Pulando execucao de {teste} devido a erro de compilacao.")

def escolher_teste():
    testes = obter_testes()
    if not testes:
        return

    print("\n=== Escolha um teste para rodar ===")
    for i, teste in enumerate(testes):
        print(f"[{i + 1}] {os.path.basename(teste)}")
    
    try:
        escolha = int(input("\nDigite o numero do teste: "))
        if 1 <= escolha <= len(testes):
            teste_escolhido = testes[escolha - 1]
            base_name = os.path.basename(teste_escolhido).replace(".minipar", "")
            success = compile_file(teste_escolhido, base_name)
            if success:
                executar_binario(base_name)
        else:
            print("[ERRO] Escolha invalida.")
    except ValueError:
        print("[ERRO] Por favor, digite um numero valido.")

def exibir_menu():
    while True:
        print("\n" + "="*45)
        print(" Menu de Testes - Compilador MiniPar 2026.1")
        print("="*45)
        print("1 - Rodar todos os testes automaticamente")
        print("2 - Escolher 1 teste para rodar")
        print("0 - Sair")
        print("="*45)
        
        opcao = input("Escolha uma opcao: ")
        
        if opcao == "1":
            rodar_todos()
        elif opcao == "2":
            escolher_teste()
        elif opcao == "0":
            print("Saindo...")
            break
        else:
            print("Opcao invalida. Tente novamente.")

if __name__ == "__main__":
    exibir_menu()