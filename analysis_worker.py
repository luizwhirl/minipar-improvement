"""Analyze one compiler phase in an isolated process using a JSON stdio protocol."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import fields, is_dataclass
import io
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ast_nodes import ForkExpr
from codegen import CppCodeGenerator, unsupported_cpp_nodes
from lexer import Lexer, TokenType
from parser import Parser
from semantic import SemanticAnalyzer
from tac import TACGenerator

PHASES = ("tokens", "ast", "semantic", "tac", "cpp")


def diagnostic(phase, message, line=None, column=None):
    return {"phase": phase, "severity": "error", "message": message,
            "line": line, "column": column}


def response(phase, result=None, diagnostics=None, failed_phase=None):
    diagnostics = diagnostics or []
    return {"success": not diagnostics, "phase": phase,
            "failed_phase": failed_phase, "result": result,
            "diagnostics": diagnostics}


def serialize_ast(value):
    if is_dataclass(value):
        return {"node_type": type(value).__name__,
                **{field.name: serialize_ast(getattr(value, field.name))
                   for field in fields(value)}}
    if isinstance(value, list):
        return [serialize_ast(item) for item in value]
    return value


def captured_diagnostics(phase, text, parser=None):
    errors = []
    token = parser._peek() if parser is not None else None
    for message in text.splitlines():
        message = message.strip()
        if not message:
            continue
        match = re.search(r"\bLinha\s+(\d+)", message)
        line = int(match.group(1)) if match else (token.line if token else None)
        col_match = re.search(r"\bcol(?:una)?\s+(\d+)", message)
        column = int(col_match.group(1)) if col_match else None
        if column is None and token is not None and token.line == line:
            column = token.col
        errors.append(diagnostic(phase, message, line, column))
    return errors or [diagnostic(phase, "A análise não pôde ser concluída.")]


def analyze(code: str, phase: str):
    """Run prerequisites only; call in the worker, never in a Flask thread."""
    if phase not in PHASES:
        raise ValueError("Fase de análise inválida.")
    if not isinstance(code, str):
        raise ValueError("O código deve ser um texto.")

    current_phase = "tokens"
    parser = None
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            token_result = {"tokens": [
                {"type": token.type.name, "lexeme": token.lexeme,
                 "line": token.line, "column": token.col}
                for token in tokens
            ]}
            errors = [diagnostic("tokens", error.message, error.line, error.col)
                      for error in lexer.errors]
            reported = {(error["line"], error["column"]) for error in errors}
            for token in tokens:
                if token.type == TokenType.UNKNOWN and (token.line, token.col) not in reported:
                    errors.append(diagnostic("tokens", f"Caractere inválido: {token.lexeme!r}.",
                                             token.line, token.col))
            if errors:
                return response(phase, token_result if phase == "tokens" else None,
                                errors, "tokens")
            if phase == "tokens":
                return response(phase, token_result)

            current_phase = "ast"
            parser = Parser(tokens)
            program = parser.parse()
            if phase == "ast":
                return response(phase, serialize_ast(program))

            current_phase = "semantic"
            if not SemanticAnalyzer().analyze(program):
                errors = captured_diagnostics(current_phase, stderr.getvalue())
                return response(phase, diagnostics=errors, failed_phase=current_phase)
            if phase == "semantic":
                return response(phase, {"valid": True,
                    "message": "Análise semântica concluída sem erros."})

            current_phase = phase
            if phase == "tac":
                return response(phase, TACGenerator().generate_text(program))

            errors = [diagnostic("cpp",
                f"A geração C++ para '{'fork' if isinstance(node, ForkExpr) else 'join'}' ainda não está implementada.",
                node.line) for node in unsupported_cpp_nodes(program)]
            if errors:
                return response(phase, diagnostics=errors, failed_phase="cpp")
            return response(phase, CppCodeGenerator().generate_text(program))
        except SystemExit:
            errors = captured_diagnostics(current_phase, stderr.getvalue(),
                                          parser if current_phase == "ast" else None)
            return response(phase, diagnostics=errors, failed_phase=current_phase)
        except RecursionError:
            errors = [diagnostic(current_phase, "O programa excede o limite de aninhamento da análise.")]
            return response(phase, diagnostics=errors, failed_phase=current_phase)
        except Exception as error:
            errors = [diagnostic(current_phase, f"Não foi possível concluir a análise: {error}")]
            return response(phase, diagnostics=errors, failed_phase=current_phase)


def main():
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    phase = None
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("A solicitação deve ser um objeto JSON.")
        phase = payload.get("phase")
        result = analyze(payload.get("code"), phase)
    except (ValueError, TypeError) as error:
        failed_phase = phase if phase in PHASES else None
        result = response(phase, diagnostics=[diagnostic(failed_phase, str(error))],
                          failed_phase=failed_phase)
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
