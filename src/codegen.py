"""
codegen.py — Gerador de Código C++ do compilador MiniPar
"""
from __future__ import annotations
import os
import subprocess
import sys
from typing import Optional

from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt,
    SeqBlock, ParBlock, BinaryExpr, UnaryExpr,
    NumberExpr, StringExpr, IdentifierExpr,
)

# Cabeçalho C++ fixo gerado em todo programa MiniPar
_CPP_HEADER = """\
#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <memory>

#ifdef _WIN32
  #include <winsock2.h>
  #pragma comment(lib, "ws2_32.lib")
#else
  #include <sys/socket.h>
  #include <arpa/inet.h>
  #include <unistd.h>
#endif

class MiniParChannel {
public:
    static void sendData(std::string ip, int port, std::string msg) {
        // Logica TCP aqui
    }
    static std::string receiveData(int port) {
        return "";
    }
};

"""


class CppCodeGenerator:
    # ------------------------------------------------------------------ #
    # Helpers privados                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _escape_string(value: str) -> str:
        """Escapa caracteres especiais para uso em strings C++."""
        result = []
        for ch in value:
            if ch == "\n":
                result.append("\\n")
            elif ch == "\t":
                result.append("\\t")
            elif ch == '"':
                result.append('\\"')
            elif ch == "\\":
                result.append("\\\\")
            else:
                result.append(ch)
        return "".join(result)

    def _translate_expression(self, node: Optional[ASTNode]) -> str:
        """Traduz um nó de expressão para C++."""
        if node is None:
            return "0"
        if isinstance(node, NumberExpr):
            return node.value
        if isinstance(node, StringExpr):
            return f'"{self._escape_string(node.value)}"'
        if isinstance(node, IdentifierExpr):
            return node.name
        if isinstance(node, UnaryExpr):
            return f"({node.op}{self._translate_expression(node.operand)})"
        if isinstance(node, BinaryExpr):
            left  = self._translate_expression(node.left)
            right = self._translate_expression(node.right)
            return f"({left} {node.op} {right})"
        return "0"

    def _translate_statement(self, node: Optional[ASTNode], indent: str = "") -> str:
        """Traduz um nó de instrução para C++."""
        if node is None:
            return ""

        if isinstance(node, VarDecl):
            expr = self._translate_expression(node.init_value)
            return f"{indent}auto {node.name} = {expr};\n"

        if isinstance(node, Assignment):
            expr = self._translate_expression(node.value)
            return f"{indent}{node.name} = {expr};\n"

        if isinstance(node, PrintStmt):
            parts = []
            for i, arg in enumerate(node.arguments):
                if i > 0:
                    parts.append(' << " "')
                parts.append(f" << {self._translate_expression(arg)}")
            return f"{indent}std::cout{''.join(parts)} << std::endl;\n"

        if isinstance(node, SeqBlock):
            lines = [f"{indent}{{\n"]
            for stmt in node.statements:
                lines.append(self._translate_statement(stmt, indent + "    "))
            lines.append(f"{indent}}}\n")
            return "".join(lines)

        if isinstance(node, ParBlock):
            lines = [f"{indent}{{\n"]
            lines.append(f"{indent}    std::vector<std::thread> __minipar_threads;\n")
            for stmt in node.statements:
                lines.append(f"{indent}    __minipar_threads.emplace_back([&]() {{\n")
                lines.append(self._translate_statement(stmt, indent + "        "))
                lines.append(f"{indent}    }});\n")
            lines.append(
                f"{indent}    for (auto& __minipar_thread : __minipar_threads) "
                f"__minipar_thread.join();\n"
            )
            lines.append(f"{indent}}}\n")
            return "".join(lines)

        return ""

    def _translate_node(self, node: Optional[ASTNode]) -> str:
        """Traduz um nó de alto nível (ex.: SeqBlock raiz) para C++."""
        if node is None:
            return ""

        if isinstance(node, SeqBlock):
            lines = ["int main() {\n"]
            lines.append("    #ifdef _WIN32\n")
            lines.append("        WSADATA wsa;\n")
            lines.append("        WSAStartup(MAKEWORD(2,2), &wsa);\n")
            lines.append("    #endif\n\n")
            for stmt in node.statements:
                lines.append(self._translate_statement(stmt, "    "))
            lines.append("\n    return 0;\n}\n")
            return "".join(lines)

        return self._translate_statement(node, "")

    # ------------------------------------------------------------------ #
    # Ponto de entrada                                                     #
    # ------------------------------------------------------------------ #

    def generate(self, program: Program, output_name: str) -> None:
        """
        Gera o código C++ a partir do programa e compila com g++.

        Args:
            program:     AST do programa MiniPar.
            output_name: Nome base do arquivo de saída (sem extensão).
        """
        cpp_code = _CPP_HEADER
        for node in program.statements:
            cpp_code += self._translate_node(node)

        os.makedirs("output", exist_ok=True)
        cpp_path = os.path.join("output", f"{output_name}.cpp")
        exe_path = os.path.join("output", f"{output_name}.exe")

        try:
            with open(cpp_path, "w", encoding="utf-8") as f:
                f.write(cpp_code)
            print(f"[CODEGEN] Codigo C++ gerado com sucesso em: {cpp_path}")
        except OSError as exc:
            print(f"[ERRO] Nao foi possivel criar o arquivo .cpp: {exc}", file=sys.stderr)
            return

        print("[CODEGEN] Invocando o compilador g++ com otimizacao -O3...")
        compile_cmd = ["g++", "-O3", cpp_path, "-o", exe_path, "-pthread", "-lws2_32"]
        result = subprocess.run(compile_cmd)

        if result.returncode == 0:
            print(f"[SUCESSO] Executavel gerado: {exe_path}")
        else:
            print("[ERRO] Falha na compilacao do g++.", file=sys.stderr)
