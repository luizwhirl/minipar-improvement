"""
Orquestrador de testes MiniPar — gerencia entradas interativas e
coordenação multi-terminal conforme especificação Compiladores2-3e4.pdf.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from datetime import datetime
from typing import Any, Optional

SESSION_FILE = os.path.join("output", ".test_session.json")
_SPINNER = ["|", "/", "-", "\\"]

# Metadados dos testes conforme documento Compiladores2-3e4.pdf
TEST_SPECS: dict[str, dict[str, Any]] = {
    "teste1_calculadora_cliente_servidor.minipar": {
        "titulo": "Programa de Teste 1 — Calculadora cliente-servidor",
        "descricao": (
            "O cliente (computador_1) solicita uma operação aritmética e o "
            "servidor (computador_2) realiza o cálculo retornando o resultado."
        ),
        "multi_computer": {
            "required": True,
            "count": 2,
            "roles": [
                "computador_1 (cliente) — envia operação e operandos",
                "computador_2 (servidor) — recebe, calcula e retorna resultado",
            ],
            "instrucoes": (
                "Abra um segundo terminal neste computador (ou em outro PC na rede) "
                "e execute o compilador MiniPar. No novo terminal, escolha "
                "'Continuar teste em andamento' para assumir o papel de computador_2."
            ),
        },
        "inputs": [
            {
                "descricao": "Operação aritmética desejada (+, -, *, /)",
                "exemplo": "+",
                "campo": "operacao",
            },
            {
                "descricao": "Operando 1 (valor numérico)",
                "exemplo": "7",
                "campo": "operando1",
            },
            {
                "descricao": "Operando 2 (valor numérico)",
                "exemplo": "5",
                "campo": "operando2",
            },
        ],
    },
    "teste2_fatorial_fibonacci_par.minipar": {
        "titulo": "Programa de Teste 2 — Fatorial e Fibonacci em PAR",
        "descricao": (
            "Thread 1 calcula fatorial; thread 2 calcula Fibonacci. "
            "Execução paralela no mesmo computador; pode ser testado em 2 computadores."
        ),
        "multi_computer": {
            "required": True,
            "count": 2,
            "roles": [
                "computador_1 — executa thread do Fatorial",
                "computador_2 — executa thread da Série de Fibonacci",
            ],
            "instrucoes": (
                "Abra um segundo terminal e execute o compilador MiniPar. "
                "Escolha 'Continuar teste em andamento' para participar como computador_2."
            ),
        },
        "inputs": [],
    },
    "teste6_quicksort_classes.minipar": {
        "titulo": "Programa de Teste 6 — Quicksort com entrada do usuário",
        "descricao": (
            "Solicita ao usuário os elementos do vetor separados por espaço "
            "via sys.stdin.readline() / input()."
        ),
        "multi_computer": None,
        "inputs": [
            {
                "descricao": "Elementos do vetor separados por espaço",
                "exemplo": "10 -3 -40 80 70 -100",
                "campo": "vetor",
            },
        ],
    },
    "teste_bnf_controles_input.minipar": {
        "titulo": "Teste BNF — Controles de fluxo com input",
        "descricao": "Demonstra for, do-while, break, continue e leitura de nome via input().",
        "multi_computer": None,
        "inputs": [
            {
                "descricao": "Nome do usuário (prompt: 'Nome: ')",
                "exemplo": "MiniPar",
                "campo": "nome",
            },
        ],
    },
    "teste_adicional1_paralelismo_3_computadores.minipar": {
        "titulo": "Teste Adicional 1 — Paralelismo com 3 computadores",
        "descricao": (
            "QuickSort no PC1, multiplicação de matrizes no PC2 e fatorial no PC3, "
            "com resultados recolhidos no computador_1."
        ),
        "multi_computer": {
            "required": True,
            "count": 3,
            "roles": [
                "computador_1 — recolhe resultados dos demais PCs",
                "computador_2 — executa QuickSort (127.0.0.1:5301)",
                "computador_3 — executa multiplicação de matrizes (127.0.0.1:5302)",
            ],
            "instrucoes": (
                "Abra mais dois terminais (total de 3 participantes). "
                "Cada terminal deve escolher 'Continuar teste em andamento' "
                "para assumir computador_2 e computador_3."
            ),
        },
        "inputs": [],
    },
}


def get_terminal_id() -> str:
    """Identificador único deste terminal/sessão."""
    hostname = socket.gethostname()
    pid = os.getpid()
    return f"{hostname}-{pid}"


def _load_session() -> Optional[dict[str, Any]]:
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_session(session: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)


def clear_session() -> None:
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


def _now_short() -> str:
    return datetime.now().strftime("%H:%M:%S")


def append_session_log(message: str, source: str = "initiator") -> None:
    """Registra evento no log compartilhado da sessão."""
    session = _load_session()
    if session is None:
        return
    log = session.setdefault("progress_log", [])
    log.append({
        "time": _now_short(),
        "message": message,
        "source": source,
    })
    if len(log) > 50:
        session["progress_log"] = log[-50:]
    _save_session(session)


def set_session_phase(phase: str, message: str, percent: Optional[int] = None) -> None:
    """Atualiza fase atual visível nos terminais participantes."""
    session = _load_session()
    if session is None:
        return
    session["phase"] = phase
    session["phase_message"] = message
    if percent is not None:
        session["progress_percent"] = percent
    _save_session(session)
    append_session_log(message, source="initiator")


def _get_participant_role(session: dict[str, Any], terminal_id: str) -> str:
    for p in session.get("participants", []):
        if p["terminal_id"] == terminal_id:
            return p["role"]
    return "participante"


def _get_role_activity(test_file: str, role: str, phase: str) -> str:
    """Mensagem contextual do papel deste terminal durante cada fase."""
    role_lower = role.lower()
    activities = {
        "waiting_participants": {
            "computador_1": "Aguardando demais computadores se conectarem...",
            "computador_2": "Conectado — aguardando início pelo computador_1...",
            "computador_3": "Conectado — aguardando início pelo computador_1...",
            "default": "Aguardando demais participantes...",
        },
        "collecting_input": {
            "computador_1": "Iniciador coletando entradas do usuário...",
            "computador_2": "Preparado para receber dados quando solicitado...",
            "computador_3": "Preparado para receber dados quando solicitado...",
            "default": "Aguardando entradas no terminal iniciador...",
        },
        "compiling": {
            "default": "Compilador processando código MiniPar no iniciador...",
        },
        "executing": {
            "cliente": "Canal aberto — pronto para enviar operação e operandos...",
            "servidor": "Canal aberto — aguardando solicitação do cliente...",
            "fatorial": "Thread de Fatorial pronta para execução paralela...",
            "fibonacci": "Thread de Fibonacci pronta para execução paralela...",
            "quicksort": "Processando QuickSort localmente...",
            "matrizes": "Processando multiplicação de matrizes...",
            "default": "Participando da execução distribuída...",
        },
        "done": {
            "default": "Teste finalizado.",
        },
    }

    phase_map = activities.get(phase, activities.get("waiting_participants", {}))

    if "cliente" in role_lower:
        return phase_map.get("cliente", phase_map.get("default", "Ativo."))
    if "servidor" in role_lower:
        return phase_map.get("servidor", phase_map.get("default", "Ativo."))
    if "fatorial" in role_lower or "computador_1" in role_lower and "fatorial" in test_file:
        if phase == "executing" and "fatorial_fibonacci" in test_file:
            return phase_map.get("fatorial", phase_map.get("default", "Ativo."))
    if "fibonacci" in role_lower or "computador_2" in role_lower and "fatorial" in test_file:
        if phase == "executing" and "fatorial_fibonacci" in test_file:
            return phase_map.get("fibonacci", phase_map.get("default", "Ativo."))
    if "quicksort" in role_lower:
        return phase_map.get("quicksort", phase_map.get("default", "Ativo."))
    if "matriz" in role_lower:
        return phase_map.get("matrizes", phase_map.get("default", "Ativo."))

    for key, msg in phase_map.items():
        if key != "default" and key in role_lower:
            return msg
    return phase_map.get("default", "Aguardando...")


def _print_joiner_header(session: dict[str, Any], my_role: str) -> None:
    _print_separator()
    print("  TERMINAL PARTICIPANTE — MONITOR DE PROGRESSO")
    _print_separator()
    print(f"\n  Terminal : {get_terminal_id()}")
    print(f"  Papel    : {my_role}")
    print(f"  Teste    : {session.get('titulo', session.get('test_file', ''))}")
    print(f"  Iniciador: {session.get('initiator_terminal', '?')}")
    print(f"\n  {'─' * 50}")
    print("  LOG DE ATIVIDADE (tempo real)")
    print(f"  {'─' * 50}\n")


def _print_joiner_summary(session: dict[str, Any], my_role: str) -> None:
    _print_separator("-")
    print("  RESUMO DO TESTE")
    _print_separator("-")
    print(f"\n  Papel deste terminal: {my_role}")
    print(f"  Status final        : {session.get('status', '?')}")
    print(f"  Participantes       : {len(session.get('participants', []))}/"
          f"{session.get('required_participants', '?')}")

    output = session.get("execution_output", "")
    if output:
        print("\n  Saída registrada pelo iniciador:")
        for line in output.strip().splitlines()[-8:]:
            print(f"    {line}")

    print(f"\n  {'─' * 50}")
    print("  Participação concluída com sucesso.")
    print(f"  {'─' * 50}\n")


def run_joiner_progress_monitor(session: dict[str, Any]) -> bool:
    """
    Exibe progresso contínuo no terminal participante enquanto o iniciador
    conduz o teste. Retorna True se concluído, False se cancelado.
    """
    terminal_id = get_terminal_id()
    my_role = _get_participant_role(session, terminal_id)
    last_log_count = 0
    spinner_idx = 0
    start_time = time.time()
    last_phase = ""

    _print_joiner_header(session, my_role)
    append_session_log(
        f"Terminal participante conectado: {my_role} ({terminal_id})",
        source="system",
    )

    while True:
        current = _load_session()
        if current is None:
            print("\n\n  [INFO] Sessão encerrada pelo iniciador.")
            return True

        log = current.get("progress_log", [])
        for entry in log[last_log_count:]:
            src = entry.get("source", "system")
            prefix = "→" if src == "initiator" else "•"
            print(f"  {prefix} [{entry['time']}] {entry['message']}")
        last_log_count = len(log)

        status = current.get("status", "waiting")
        phase = current.get("phase", "waiting_participants")
        phase_msg = current.get("phase_message", "Aguardando...")
        role_activity = _get_role_activity(current.get("test_file", ""), my_role, phase)
        percent = current.get("progress_percent")
        elapsed = int(time.time() - start_time)
        spinner = _SPINNER[spinner_idx % len(_SPINNER)]
        spinner_idx += 1

        if phase != last_phase:
            print(f"\n  ▶ Fase: {phase_msg}")
            last_phase = phase

        bar = ""
        if percent is not None:
            filled = int(percent / 5)
            bar = f" [{'█' * filled}{'░' * (20 - filled)}] {percent}%"

        sys.stdout.write(
            f"\r  {spinner} [{elapsed:>3}s]{bar} {role_activity}          "
        )
        sys.stdout.flush()

        if status == "completed":
            print("\n")
            _print_joiner_summary(current, my_role)
            return True
        if status == "cancelled":
            print("\n\n  [INFO] Teste cancelado pelo iniciador.")
            return False

        time.sleep(0.4)


def record_execution_output(text: str) -> None:
    """Salva saída parcial da execução para exibir nos terminais participantes."""
    session = _load_session()
    if session is None:
        return
    session["execution_output"] = text
    _save_session(session)


def get_test_spec(filename: str) -> Optional[dict[str, Any]]:
    return TEST_SPECS.get(os.path.basename(filename))


def _print_separator(char: str = "=", width: int = 55) -> None:
    print(char * width)


def prompt_new_user_on_active_session(session: dict[str, Any]) -> str:
    """
    Quando há sessão ativa e um novo terminal executa o programa.
    Retorna 'join' ou 'independent'.
    """
    spec = TEST_SPECS.get(session.get("test_file", ""), {})
    titulo = spec.get("titulo", session.get("test_file", "desconhecido"))
    participantes = session.get("participants", [])
    required = session.get("required_participants", 0)
    iniciador = session.get("initiator_terminal", "?")

    _print_separator()
    print("  SESSÃO DE TESTE EM ANDAMENTO DETECTADA")
    _print_separator()
    print(f"\n  Teste: {titulo}")
    print(f"  Iniciado por: {iniciador}")
    print(f"  Participantes conectados: {len(participantes)}/{required}")
    for p in participantes:
        print(f"    - {p['role']} ({p['terminal_id']})")

    print(f"\n  Você foi identificado como: {get_terminal_id()}\n")
    print("  O que deseja fazer?\n")
    print("  [1] Executar o código de forma independente (ignorar teste em andamento)")
    print("  [2] Continuar e participar do teste em andamento\n")

    while True:
        escolha = input("  Digite sua escolha (1 ou 2): ").strip()
        if escolha == "1":
            return "independent"
        if escolha == "2":
            return "join"
        print("  [ERRO] Escolha inválida. Digite 1 ou 2.")


def _assign_role(session: dict[str, Any]) -> Optional[str]:
    """Atribui próximo papel disponível ao terminal que está entrando."""
    spec = TEST_SPECS.get(session.get("test_file", ""), {})
    multi = spec.get("multi_computer") or {}
    roles = multi.get("roles", [])
    taken = {p["role"] for p in session.get("participants", [])}

    for role in roles:
        if role not in taken:
            return role
    return None


def join_session(session: dict[str, Any]) -> dict[str, Any]:
    """Adiciona este terminal à sessão ativa."""
    terminal_id = get_terminal_id()
    participants = session.get("participants", [])

    if any(p["terminal_id"] == terminal_id for p in participants):
        print(f"\n  [INFO] Terminal {terminal_id} já participa desta sessão.")
        return session

    role = _assign_role(session)
    if role is None:
        print("\n  [AVISO] Todos os papéis já foram atribuídos. Aguardando execução...")
        return session

    participants.append({
        "terminal_id": terminal_id,
        "role": role,
        "ready": True,
        "joined_at": datetime.now().isoformat(),
    })
    session["participants"] = participants
    session.setdefault("progress_log", [])
    _save_session(session)
    append_session_log(f"Participante entrou: {role} ({terminal_id})", source="system")

    print(f"\n  [OK] Você entrou como: {role}")
    print(f"  Participantes: {len(participants)}/{session['required_participants']}")
    return session


def create_session(test_file: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Cria sessão multi-terminal para um teste."""
    multi = spec["multi_computer"]
    terminal_id = get_terminal_id()
    roles = multi.get("roles", [])

    session = {
        "test_file": os.path.basename(test_file),
        "titulo": spec.get("titulo", test_file),
        "required_participants": multi["count"],
        "initiator_terminal": terminal_id,
        "status": "waiting",
        "phase": "waiting_participants",
        "phase_message": "Aguardando participantes adicionais...",
        "progress_percent": 0,
        "progress_log": [],
        "execution_output": "",
        "created_at": datetime.now().isoformat(),
        "participants": [{
            "terminal_id": terminal_id,
            "role": roles[0] if roles else "computador_1",
            "ready": True,
            "joined_at": datetime.now().isoformat(),
        }],
    }
    _save_session(session)
    append_session_log(
        f"Sessão criada pelo iniciador ({terminal_id}) — "
        f"aguardando {multi['count'] - 1} terminal(is) adicional(is).",
        source="system",
    )
    return session


def _wait_for_participants(session: dict[str, Any], spec: dict[str, Any]) -> bool:
    """Aguarda participantes adicionais antes de prosseguir."""
    multi = spec["multi_computer"]
    required = multi["count"]
    terminal_id = get_terminal_id()

    _print_separator()
    print("  TESTE MULTI-COMPUTADOR")
    _print_separator()
    print(f"\n  {spec.get('titulo', '')}")
    print(f"\n  {spec.get('descricao', '')}\n")
    print(f"  Este teste exige {required} computador(es/terminais).\n")
    print("  Papéis necessários:")
    for i, role in enumerate(multi.get("roles", []), 1):
        print(f"    [{i}] {role}")
    print(f"\n  {multi.get('instrucoes', '')}\n")
    print(f"  Seu terminal ({terminal_id}) é o iniciador.")
    print(f"  Participantes conectados: 1/{required}\n")
    print("  Abra o(s) terminal(is) adicional(is) e execute:")
    print("    python main.py")
    print("  Em seguida, escolha 'Continuar teste em andamento'.\n")

    input("  Pressione ENTER quando o(s) outro(s) terminal(is) estiver(em) pronto(s)... ")

    print("\n  Monitorando conexões dos participantes...\n")
    last_count = 1
    for tick in range(60):
        current = _load_session()
        if not current:
            break
        connected = len(current.get("participants", []))
        if connected > last_count:
            for p in current["participants"][last_count:]:
                print(f"  ✓ Conectado: {p['role']} ({p['terminal_id']})")
            last_count = connected
            pct = min(int((connected / required) * 40), 40)
            set_session_phase(
                "waiting_participants",
                f"{connected}/{required} participantes conectados",
                percent=pct,
            )

        sys.stdout.write(
            f"\r  Aguardando... {connected}/{required} participantes conectados"
            f"  ({tick + 1}s)   "
        )
        sys.stdout.flush()

        if connected >= required:
            print(f"\n\n  [OK] {required} participantes conectados. Prosseguindo...\n")
            current["status"] = "ready"
            set_session_phase(
                "waiting_participants",
                "Todos os participantes conectados",
                percent=40,
            )
            _save_session(current)
            return True
        time.sleep(0.5)

    current = _load_session()
    connected = len(current.get("participants", [])) if current else 1
    print(f"\n  [AVISO] Apenas {connected}/{required} participante(s) detectado(s).")
    resposta = input("  Deseja continuar mesmo assim? (s/n): ").strip().lower()
    if resposta in ("s", "sim", "y", "yes"):
        if current:
            current["status"] = "ready"
            _save_session(current)
        return True
    clear_session()
    print("  [INFO] Teste cancelado.")
    return False


def _wait_as_joiner(session: dict[str, Any]) -> bool:
    """Terminal participante aguarda o iniciador concluir, exibindo progresso."""
    return run_joiner_progress_monitor(session)


def collect_inputs(spec: dict[str, Any]) -> list[str]:
    """Solicita entradas ao usuário conforme especificação do PDF."""
    inputs_spec = spec.get("inputs", [])
    if not inputs_spec:
        return []

    _print_separator()
    print("  ENTRADA DO USUÁRIO NECESSÁRIA")
    _print_separator()
    print(f"\n  {spec.get('titulo', '')}")
    print(f"\n  {spec.get('descricao', '')}\n")
    print("  Este teste exige entrada do teclado antes de continuar.")
    print("  Insira os valores conforme especificado no documento:\n")

    collected: list[str] = []
    for i, inp in enumerate(inputs_spec, 1):
        exemplo = inp.get("exemplo", "")
        desc = inp.get("descricao", f"Entrada {i}")
        print(f"  [{i}] {desc}")
        if exemplo:
            print(f"      Exemplo do documento: {exemplo}")

        while True:
            valor = input(f"      Digite o valor (ENTER = usar exemplo '{exemplo}'): ").strip()
            if not valor and exemplo:
                valor = exemplo
            if valor:
                collected.append(valor)
                break
            print("      [ERRO] Informe um valor ou pressione ENTER para usar o exemplo.")

    print("\n  [OK] Entradas registradas. Prosseguindo com a execução...\n")
    return collected


def check_active_session_for_new_terminal() -> tuple[Optional[str], Optional[dict]]:
    """
    Verifica se há sessão ativa quando um novo terminal inicia.
    Retorna (action, session) onde action é None, 'independent', ou 'join'.
    """
    session = _load_session()
    if session is None or session.get("status") in ("completed", "cancelled"):
        return None, session

    if session.get("status") == "running":
        # Outro terminal já está executando
        action = prompt_new_user_on_active_session(session)
        return action, session

    if session.get("status") in ("waiting", "ready"):
        terminal_id = get_terminal_id()
        participants = session.get("participants", [])

        if any(p["terminal_id"] == terminal_id for p in participants):
            return None, session

        if len(participants) < session.get("required_participants", 0):
            action = prompt_new_user_on_active_session(session)
            return action, session

    return None, session


def prepare_test_execution(test_path: str) -> tuple[bool, list[str], bool]:
    """
    Prepara execução de um teste com orquestração.
    Retorna (proceed, stdin_lines, is_joiner).
    """
    filename = os.path.basename(test_path)
    spec = get_test_spec(filename)
    stdin_lines: list[str] = []
    is_joiner = False

    # Verifica sessão ativa (terminal secundário)
    active_session = _load_session()
    if active_session and active_session.get("test_file") != filename:
        action, _ = check_active_session_for_new_terminal()
        if action == "join":
            join_session(active_session)
            if not _wait_as_joiner(active_session):
                return False, [], True
            is_joiner = True
            spec = get_test_spec(active_session["test_file"]) or spec
            filename = active_session["test_file"]

    if spec is None:
        return True, [], is_joiner

    # Multi-computador
    multi = spec.get("multi_computer")
    if multi and multi.get("required"):
        session = _load_session()
        terminal_id = get_terminal_id()

        if session and session.get("test_file") == filename:
            participants = session.get("participants", [])
            is_initiator = (
                session.get("initiator_terminal") == terminal_id
                or (participants and participants[0]["terminal_id"] == terminal_id)
            )

            if not is_initiator:
                if not any(p["terminal_id"] == terminal_id for p in participants):
                    action, _ = check_active_session_for_new_terminal()
                    if action == "join":
                        join_session(session)
                    elif action == "independent":
                        clear_session()
                        session = create_session(test_path, spec)
                        is_initiator = True
                    else:
                        return False, [], False

                if not is_initiator:
                    if not _wait_as_joiner(session):
                        return False, [], True
                    return True, [], True
            else:
                if not _wait_for_participants(session, spec):
                    return False, [], False
        else:
            session = create_session(test_path, spec)
            if not _wait_for_participants(session, spec):
                return False, [], False

        session = _load_session()
        if session:
            session["status"] = "running"
            set_session_phase("collecting_input", "Preparando execução do teste...", percent=45)
            _save_session(session)

    # Entrada do usuário
    inputs_spec = spec.get("inputs", [])
    if inputs_spec:
        set_session_phase("collecting_input", "Coletando entradas do usuário...", percent=50)
        stdin_lines = collect_inputs(spec)
        append_session_log("Entradas do usuário registradas no terminal iniciador.")

    return True, stdin_lines, is_joiner


def finalize_test_execution(test_path: str, output: str = "") -> None:
    """Marca sessão como concluída após execução."""
    filename = os.path.basename(test_path)
    session = _load_session()
    if session and session.get("test_file") == filename:
        if output:
            session["execution_output"] = output
        session["status"] = "completed"
        session["phase"] = "done"
        session["phase_message"] = "Teste concluído com sucesso!"
        session["progress_percent"] = 100
        log = session.setdefault("progress_log", [])
        log.append({
            "time": _now_short(),
            "message": "Teste finalizado pelo terminal iniciador.",
            "source": "initiator",
        })
        _save_session(session)
        time.sleep(2)
        clear_session()


def get_spec_summary(filename: str) -> Optional[dict[str, Any]]:
    """Retorna resumo do spec para API web."""
    spec = get_test_spec(filename)
    if spec is None:
        return None
    return {
        "titulo": spec.get("titulo", ""),
        "descricao": spec.get("descricao", ""),
        "requires_input": bool(spec.get("inputs")),
        "inputs": spec.get("inputs", []),
        "multi_computer": spec.get("multi_computer"),
    }
