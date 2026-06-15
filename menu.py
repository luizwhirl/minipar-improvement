import os
import sys
import subprocess
import glob

from main import compile_file
from test_orchestrator import (
    prepare_test_execution,
    finalize_test_execution,
    check_active_session_for_new_terminal,
    join_session,
    get_test_spec,
    get_terminal_id,
    set_session_phase,
    append_session_log,
    record_execution_output,
    run_joiner_progress_monitor,
    _load_session,
)


def executar_binario(output_name: str, stdin_lines: list[str] | None = None) -> str:
    """Executa o arquivo gerado apos a compilacao, com stdin opcional. Retorna stdout."""
    exe_ext = ".exe" if sys.platform == "win32" else ""
    exe_path = os.path.join("output", f"{output_name}{exe_ext}")

    if not os.path.exists(exe_path):
        print(f"[ERRO] Executavel {exe_path} nao encontrado apos compilacao.")
        return ""

    abs_exe_path = os.path.abspath(exe_path)
    print(f"\n--- Executando {output_name} ---")
    set_session_phase("executing", f"Executando {output_name}...", percent=85)
    append_session_log(f"Binário {output_name} em execução no terminal iniciador.")
    try:
        stdin_data = None
        if stdin_lines:
            stdin_data = "\n".join(stdin_lines) + "\n"
        result = subprocess.run(
            [abs_exe_path],
            input=stdin_data,
            text=True,
            capture_output=True,
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        if output.strip():
            print(output)
            record_execution_output(output)
            append_session_log("Saída do programa registrada.")
    except Exception as e:
        print(f"[ERRO] Falha ao executar {exe_path}: {e}")
        return ""
    print("-" * 40)
    return output


def _exibir_info_teste(test_path: str) -> None:
    """Mostra informações do teste conforme documento PDF."""
    spec = get_test_spec(os.path.basename(test_path))
    if spec is None:
        return
    print(f"\n  Teste: {spec.get('titulo', '')}")
    if spec.get("descricao"):
        print(f"  {spec['descricao']}")


def rodar_teste(test_path: str) -> None:
    """Compila e executa um teste com orquestração de entrada e multi-terminal."""
    base_name = os.path.basename(test_path).replace(".minipar", "")

    _exibir_info_teste(test_path)

    proceed, stdin_lines, is_joiner = prepare_test_execution(test_path)
    if not proceed:
        return

    if is_joiner:
        print(f"\n  Terminal participante: {get_terminal_id()}\n")
        return

    set_session_phase("compiling", "Iniciando compilação MiniPar...", percent=55)
    append_session_log("Compilação iniciada (análise léxica, sintática, semântica).")
    success = compile_file(test_path, base_name)
    if success:
        set_session_phase("compiling", "Compilação concluída — gerando executável.", percent=80)
        append_session_log("Compilação concluída com sucesso.")
        output = executar_binario(base_name, stdin_lines if stdin_lines else None)
        finalize_test_execution(test_path, output)
    else:
        append_session_log("Erro na compilação — execução abortada.")
        print(f"[AVISO] Pulando execucao de {test_path} devido a erro de compilacao.")


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
        rodar_teste(teste)


def escolher_teste():
    testes = obter_testes()
    if not testes:
        return

    print("\n=== Escolha um teste para rodar ===")
    for i, teste in enumerate(testes):
        nome = os.path.basename(teste)
        spec = get_test_spec(nome)
        tags = []
        if spec:
            if spec.get("inputs"):
                tags.append("entrada")
            if spec.get("multi_computer"):
                tags.append(f"{spec['multi_computer']['count']} PCs")
        tag_str = f"  [{', '.join(tags)}]" if tags else ""
        print(f"[{i + 1}] {nome}{tag_str}")

    try:
        escolha = int(input("\nDigite o numero do teste: "))
        if 1 <= escolha <= len(testes):
            rodar_teste(testes[escolha - 1])
        else:
            print("[ERRO] Escolha invalida.")
    except ValueError:
        print("[ERRO] Por favor, digite um numero valido.")


def _verificar_sessao_ao_iniciar() -> bool:
    """
    Ao abrir o menu, verifica se há teste multi-terminal em andamento.
    Retorna True se este terminal entrou como participante e deve aguardar.
    """
    action, session = check_active_session_for_new_terminal()
    if action == "join" and session:
        join_session(session)
        session = _load_session() or session
        print(f"\n  [OK] Você entrou no teste em andamento.")
        print(f"  Terminal: {get_terminal_id()}\n")
        run_joiner_progress_monitor(session)
        return True
    if action == "independent":
        print("\n  [INFO] Modo independente — sessão em andamento ignorada.\n")
    return False


def exibir_menu():
    _verificar_sessao_ao_iniciar()

    while True:
        print("\n" + "=" * 45)
        print(" Menu de Testes - Compilador MiniPar 2026.1")
        print("=" * 45)
        print("1 - Rodar todos os testes automaticamente")
        print("2 - Escolher 1 teste para rodar")
        print("0 - Sair")
        print("=" * 45)

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
