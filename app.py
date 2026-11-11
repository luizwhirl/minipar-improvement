from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file, url_for, abort
import subprocess
import os
import sys
import glob
import json
from pathlib import Path
import web_execution
from run_artifacts import create_run_dir, executable_path

from test_orchestrator import (
    get_spec_summary,
    finalize_test_execution,
    inspect_active_session,
    load_completed_session,
    join_session,
    get_terminal_id,
    create_session,
    clear_session,
    set_session_phase,
    append_session_log,
    record_execution_output,
    _load_session,
    _save_session,
)

app = Flask(__name__)
app.config.update(WEB_COMPILE_TIMEOUT=15, WEB_EXECUTE_TIMEOUT=30, WEB_OUTPUT_LIMIT=2 * 1024 * 1024)
BUILD_DOWNLOADS = web_execution.DownloadRegistry()

# Configuração de Diretórios
TESTS_DIR = 'tests'
OUTPUT_DIR = 'output'
TEMP_DIR = 'temp_code'

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/legacy', methods=['GET'])
def legacy():
    return render_template('legacy.html')

@app.route('/api/tests', methods=['GET'])
def get_tests():
    # Retorna os testes ordenados alfabeticamente
    tests = [os.path.basename(f) for f in glob.glob(os.path.join(TESTS_DIR, '*.minipar'))]
    return jsonify({"tests": sorted(tests)})

@app.route('/api/get_test', methods=['POST'])
def get_test():
    filename = request.json.get('filename')
    filepath = os.path.join(TESTS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify({"code": f.read()})
    return jsonify({"error": "Arquivo não encontrado"}), 404

@app.route('/api/test_spec', methods=['POST'])
def get_test_spec_api():
    """Requisitos detectados automaticamente pelo program_analyzer."""
    filename = request.json.get('filename')
    spec = get_spec_summary(filename)
    if spec:
        return jsonify(spec)
    return jsonify({"requires_input": False, "multi_computer": None})


@app.route('/api/session', methods=['GET'])
def get_session():
    needs_choice, session = inspect_active_session()
    created_at = request.args.get('created_at')
    if created_at and (not session or session.get('created_at') != created_at):
        session = load_completed_session(created_at)
        needs_choice = False
    if session:
        return jsonify({
            "active": session.get("status") not in ("completed", "cancelled"),
            "session": session,
            "terminal_id": get_terminal_id(),
            "needs_choice": needs_choice,
        })
    return jsonify({"active": False, "terminal_id": get_terminal_id()})


@app.route('/api/session/join', methods=['POST'])
def session_join():
    _, session = inspect_active_session()
    if session and session.get("status") not in ("completed", "cancelled"):
        join_session(session)
        return jsonify({"success": True, "session": session})
    return jsonify({"success": False, "error": "Nenhuma sessão ativa"}), 404


@app.route('/api/session/create', methods=['POST'])
def session_create():
    filename = request.json.get('filename')
    path = os.path.join(TESTS_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Arquivo não encontrado"}), 404
    from program_analyzer import get_program_spec
    spec = get_program_spec(path)
    if not spec.get('multi_computer'):
        return jsonify({"success": False, "error": "Programa não requer multi-terminal"}), 400
    session = create_session(path, spec)
    return jsonify({"success": True, "session": session})


@app.route('/api/session/ready', methods=['POST'])
def session_ready():
    session = _load_session()
    if session:
        session["status"] = "running"
        _save_session(session)
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


@app.route('/api/session/clear', methods=['POST'])
def session_clear():
    clear_session()
    return jsonify({"success": True})


@app.route('/api/analyze', methods=['POST'])
def analyze_phase():
    """Inspect one compiler phase without compiling or running the program."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Envie um objeto JSON com código e fase."}), 400
    code = data.get("code")
    phase = data.get("phase")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Informe o código MiniPar que deseja analisar."}), 400
    if not isinstance(phase, str) or phase not in ("tokens", "ast", "semantic", "tac", "cpp"):
        return jsonify({"error": "Fase inválida. Escolha Tokens, AST, Semântica, TAC ou C++."}), 400

    try:
        # Parser diagnostics currently use sys.exit()/stderr. Keep each analysis
        # in its own process so concurrent web requests retain separate output.
        process = subprocess.run(
            [sys.executable, "-X", "utf8", "-B", os.path.join(app.root_path, "analysis_worker.py")],
            input=json.dumps({"code": code, "phase": phase}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            cwd=app.root_path,
        )
        if process.returncode != 0:
            app.logger.error("Falha no processo de análise: %s", process.stderr)
            return jsonify({"error": "Não foi possível concluir a análise do código."}), 500
        result = json.loads(process.stdout)
        if (
            not isinstance(result, dict)
            or result.get("phase") != phase
            or not isinstance(result.get("success"), bool)
            or not isinstance(result.get("diagnostics"), list)
            or "result" not in result
            or "failed_phase" not in result
        ):
            raise ValueError("Resposta inválida do processo de análise")
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "A análise excedeu o tempo limite de 15 segundos."}), 504
    except (OSError, ValueError, UnicodeError):
        app.logger.exception("Falha ao processar a análise da fase %s", phase)
        return jsonify({"error": "Não foi possível concluir a análise do código."}), 500


def _compiler_command(run):
    return [sys.executable, "-X", "utf8", "-u", "-B", os.path.join(app.root_path, "main.py"),
            str(run.source), run.stem, "--output-dir", str(run.directory)]


def _process_failure(result, phase):
    if result.timed_out:
        return f"Tempo limite de {phase} excedido."
    if result.output_limited:
        return "O programa excedeu o limite de saída permitido."
    if result.exit_code != 0:
        return f"A {phase} terminou com código de saída {result.exit_code}."
    return None


def _download_for(run):
    token, filename = BUILD_DOWNLOADS.register(run)
    return url_for("download_build", run_id=token, filename=filename)


class _ExecutionSessionGuard:
    """Associate writes only with this owner, source and session generation."""
    def __init__(self, code, filename):
        self.code = code
        self.filename = filename
        self.source = Path(TESTS_DIR) / filename
        self.created_at = None
        try:
            session = _load_session() if self._source_matches() else None
            if self._owns(session):
                self.created_at = session.get("created_at")
        except (OSError, UnicodeError, ValueError):
            pass

    def _source_matches(self):
        return (isinstance(self.code, str) and self.source.is_file()
            and self.source.read_text(encoding="utf-8").replace("\r\n", "\n")
                == self.code.replace("\r\n", "\n"))

    def _owns(self, session):
        return (isinstance(session, dict)
            and session.get("initiator_terminal") == get_terminal_id()
            and session.get("test_file") == self.filename
            and session.get("status") not in ("completed", "cancelled"))

    def _current(self):
        if self.created_at is None or not self._source_matches():
            return None
        session = _load_session()
        if self._owns(session) and session.get("created_at") == self.created_at:
            return session
        return None

    def call(self, function, *args, **kwargs):
        try:
            if self._current() is not None:
                function(*args, **kwargs)
        except (OSError, UnicodeError, ValueError):
            app.logger.warning("Não foi possível atualizar a sessão da execução.")

    def cancel(self, message):
        try:
            session = self._current()
            if session is not None:
                session.update(status="cancelled", phase="cancelled", phase_message=message)
                _save_session(session)
        except (OSError, UnicodeError, ValueError):
            app.logger.warning("Não foi possível encerrar a sessão da execução.")


@app.route('/api/build', methods=['POST'])
def build_program():
    """Compile and offer this build's binary without executing or changing sessions."""
    try:
        code, filename, _ = web_execution.validate_source(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        run = web_execution.prepare_run(code, filename, OUTPUT_DIR)
        result = web_execution.run_capture(_compiler_command(run), cwd=app.root_path,
            timeout=app.config["WEB_COMPILE_TIMEOUT"], output_limit=app.config["WEB_OUTPUT_LIMIT"])
        failure = _process_failure(result, "compilação")
        if not failure and not run.executable.is_file():
            failure = "O compilador não produziu um executável."
        success = failure is None
        artifacts = web_execution.read_artifacts(run) if success else {"cpp": "", "tac": ""}
        return jsonify({"success": success, "stdout": result.stdout,
            "stderr": result.stderr + (("\n" if result.stderr else "") + failure if failure else ""),
            **artifacts, "download_url": _download_for(run) if success else None,
            "filename": run.executable.name})
    except Exception:
        app.logger.exception("Falha na compilação para download")
        return jsonify({"success": False, "stdout": "", "stderr": "Não foi possível compilar o programa.",
                        "cpp": "", "tac": "", "download_url": None, "filename": None}), 500


@app.route('/api/download/<run_id>/<filename>', methods=['GET'])
def download_build(run_id, filename):
    path = BUILD_DOWNLOADS.lookup(run_id, filename, OUTPUT_DIR)
    if path is None:
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename,
                     mimetype="application/octet-stream", max_age=0)


@app.route('/api/execute', methods=['POST'])
def execute_program():
    """Compile and stream decoded output from the current program."""
    try:
        code, filename, inputs = web_execution.validate_source(request.get_json(silent=True), with_inputs=True)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    def events():
        run = None
        artifacts = {"cpp": "", "tac": ""}
        stdout, stderr = "", ""
        exit_code = None
        success = False
        finished = False
        session = _ExecutionSessionGuard(code, filename)
        session_call = session.call
        cancel_session = session.cancel

        def ndjson(event):
            return json.dumps(event, ensure_ascii=False) + "\n"

        try:
            yield ndjson({"type": "phase", "phase": "compiling", "message": "Compilando código MiniPar..."})
            run = web_execution.prepare_run(code, filename, OUTPUT_DIR)
            session_call(set_session_phase, "compiling", "Compilando código MiniPar...", percent=60)
            session_call(append_session_log, "Compilação iniciada via IDE Web.")
            iterator = web_execution.iter_process(_compiler_command(run), cwd=app.root_path,
                timeout=app.config["WEB_COMPILE_TIMEOUT"], output_limit=app.config["WEB_OUTPUT_LIMIT"])
            try:
                while True:
                    try:
                        event = next(iterator)
                    except StopIteration as done:
                        compilation = done.value
                        break
                    yield ndjson(event)
            finally:
                iterator.close()
            stdout, stderr = compilation.stdout, compilation.stderr
            exit_code = compilation.exit_code
            failure = _process_failure(compilation, "compilação")
            if not failure and not run.executable.is_file():
                failure = "O compilador não produziu um executável."
            if failure:
                stderr += ("\n" if stderr else "") + failure
                yield ndjson({"type": "error", "message": failure, "phase": "compiling"})
            else:
                artifacts = web_execution.read_artifacts(run)
                yield ndjson({"type": "phase", "phase": "executing", "message": "Executando o programa..."})
                session_call(set_session_phase, "executing", "Executando o programa...", percent=90)
                session_call(append_session_log, "Compilação concluída — executando binário.")
                iterator = web_execution.iter_process([str(run.executable)], cwd=app.root_path,
                    timeout=app.config["WEB_EXECUTE_TIMEOUT"],
                    stdin_data="\n".join(inputs) + "\n" if inputs else None,
                    output_limit=app.config["WEB_OUTPUT_LIMIT"])
                try:
                    while True:
                        try:
                            event = next(iterator)
                        except StopIteration as done:
                            execution = done.value
                            break
                        yield ndjson(event)
                finally:
                    iterator.close()
                stdout += execution.stdout
                stderr += execution.stderr
                exit_code = execution.exit_code
                failure = _process_failure(execution, "execução")
                success = failure is None
                session_call(record_execution_output, execution.stdout)
                if failure:
                    stderr += ("\n" if stderr else "") + failure
                    yield ndjson({"type": "error", "message": failure, "phase": "executing"})
                if success:
                    session_call(finalize_test_execution, str(session.source), stdout)
            if not success:
                cancel_session("Execução não concluída.")
            finished = True
            yield ndjson({"type": "complete", "success": success, "exit_code": exit_code,
                "stdout": stdout, "stderr": stderr, **artifacts,
                "download_url": _download_for(run) if success else None,
                "filename": run.executable.name})
        except GeneratorExit:
            raise
        except Exception:
            app.logger.exception("Falha na execução Web")
            message = "Não foi possível concluir a execução do programa."
            cancel_session(message)
            yield ndjson({"type": "error", "message": message})
            finished = True
            yield ndjson({"type": "complete", "success": False, "exit_code": exit_code,
                "stdout": stdout, "stderr": message, **artifacts,
                "download_url": None, "filename": run.executable.name if run else None})
        finally:
            if not finished:
                cancel_session("Execução interrompida.")

    return Response(stream_with_context(events()), mimetype="application/x-ndjson",
                    headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code')
    filename = os.path.basename(data.get('filename', 'ide_temp.minipar'))
    user_inputs = data.get('inputs', [])
    session = _ExecutionSessionGuard(code, filename)
    
    # Salva o código recebido da IDE em um arquivo temporário
    output_dir = create_run_dir(OUTPUT_DIR)
    source_dir = os.path.join(output_dir, "source")
    os.makedirs(source_dir)
    file_path = os.path.join(source_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
        
    base_name = filename.replace('.minipar', '')
    stdin_lines = user_inputs  # valores coletados pela IDE para input() no .minipar
    
    try:
        session.call(set_session_phase, "compiling", "Compilando código MiniPar...", percent=60)
        session.call(append_session_log, "Compilação iniciada via IDE Web.")
        # ==========================================
        # 1. FASE DE COMPILAÇÃO (Gera TAC e C++)
        # ==========================================
        process = subprocess.run(
            [sys.executable, os.path.join(app.root_path, 'main.py'), file_path,
             base_name, '--output-dir', output_dir],
            capture_output=True, 
            text=True, 
            timeout=15
        )
        
        # Junta logs do sistema
        full_output = process.stdout
        if process.stderr:
            full_output += "\n" + process.stderr
            
        success = process.returncode == 0

        # ==========================================
        # 2. FASE DE EXECUÇÃO (Roda o Binário C++)
        # ==========================================
        if success:
            session.call(set_session_phase, "compiling", "Compilação concluída.", percent=80)
            session.call(append_session_log, "Compilação concluída — executando binário.")
            exe_path = executable_path(output_dir, base_name)
            
            if os.path.exists(exe_path):
                full_output += f"\n--- Executando {base_name} ---\n"
                session.call(set_session_phase, "executing", f"Executando {base_name}...", percent=90)
                try:
                    stdin_data = None
                    if stdin_lines:
                        stdin_data = "\n".join(stdin_lines) + "\n"
                    exe_proc = subprocess.run(
                        [os.path.abspath(exe_path)], 
                        input=stdin_data,
                        capture_output=True, 
                        text=True, 
                        timeout=30
                    )
                    full_output += exe_proc.stdout
                    if exe_proc.stderr:
                        full_output += "\n[ERRO NA EXECUÇÃO]:\n" + exe_proc.stderr
                    session.call(record_execution_output, exe_proc.stdout or "")
                    if exe_proc.returncode != 0:
                        full_output += f"\n[ERRO] Programa encerrado com código de saída {exe_proc.returncode}."
                        success = False
                except subprocess.TimeoutExpired:
                    full_output += "\n[ERRO] Tempo limite de execução excedido (O programa entrou em loop infinito ou aguarda entrada de dados do usuário?)."
                    success = False
                except Exception as e:
                    full_output += f"\n[ERRO] Falha ao executar binário: {e}"
                    success = False
                
                full_output += "\n" + "-" * 40

                if success:
                    session.call(finalize_test_execution, str(session.source), full_output)
            else:
                full_output += "\n[ERRO] O compilador não produziu um executável."
                success = False

        if not success:
            session.cancel("Compilação ou execução não concluída.")
        
        # ==========================================
        # 3. COLETA DOS ARQUIVOS GERADOS
        # ==========================================
        cpp_file = os.path.join(output_dir, f"{base_name}.cpp")
        tac_file = os.path.join(output_dir, f"{base_name}.tac")
        
        cpp_code = ""
        tac_code = ""
        
        if os.path.exists(cpp_file):
            with open(cpp_file, 'r', encoding='utf-8') as f:
                cpp_code = f.read()
                
        if os.path.exists(tac_file):
             with open(tac_file, 'r', encoding='utf-8') as f:
                tac_code = f.read()
                
        # Retorna o resultado. Se der erro, colocamos o log completo em stderr para o JS puxar
        return jsonify({
            "stdout": full_output if success else "",
            "stderr": full_output if not success else "",
            "cpp": cpp_code,
            "tac": tac_code,
            "success": success
        })
        
    except subprocess.TimeoutExpired:
        session.cancel("Tempo limite do compilador excedido.")
        return jsonify({"error": "Tempo limite do compilador excedido.", "success": False}), 500
    except Exception as e:
        session.cancel("Não foi possível concluir a execução do programa.")
        return jsonify({"error": str(e), "success": False}), 500

if __name__ == '__main__':
    # Roda a IDE silenciosamente
    app.run(debug=False, port=5000)
