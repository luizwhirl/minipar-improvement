from __future__ import annotations
import os
import subprocess
import sys
from typing import Optional
from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt, SeqBlock, ParBlock, BinaryExpr, 
    UnaryExpr, NumberExpr, StringExpr, IdentifierExpr, IfStmt, WhileStmt,
    ClassDecl, FuncDecl, ReturnStmt, MethodCall, PropertyAccess, PropertyAssign, NewExpr, ThisExpr,
    CChannelExpr, SendStmt, ReceiveExpr, ListLiteral, MatrixCreateExpr, IndexExpr, IndexAssign
)

_CPP_HEADER = """\
#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <memory>
#include <cstring>
#include <chrono>
#include <type_traits>

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  #define CLOSE_SOCK closesocket
#else
  #include <sys/socket.h>
  #include <arpa/inet.h>
  #include <unistd.h>
  #define CLOSE_SOCK close
#endif

// Helper para formatar e printar std::vector (arrays e matrizes) nativamente
template <typename T>
std::ostream& operator<<(std::ostream& os, const std::vector<T>& v) {
    os << "[";
    for (size_t i = 0; i < v.size(); ++i) {
        os << v[i];
        if (i != v.size() - 1) os << ", ";
    }
    os << "]";
    return os;
}

// Helper para enviar números ou strings via Sockets
template<typename T>
std::string __to_string(const T& val) {
    if constexpr (std::is_constructible_v<std::string, T>) {
        return std::string(val);
    } else {
        return std::to_string(val);
    }
}

// Helper para criar matrizes 2D protegidas dinamicamente
template<typename T>
auto __make_matrix(int rows, int cols, T init_val) {
    using ActualT = std::conditional_t<std::is_same_v<std::decay_t<T>, const char*>, std::string, T>;
    return std::vector<std::vector<ActualT>>(rows, std::vector<ActualT>(cols, init_val));
}

class MiniParChannel {
public:
    std::string ip;
    int port;

    MiniParChannel(std::string ip, int port) : ip(ip), port(port) {}

    void sendData(std::string msg) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) return;
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip.c_str(), &serv_addr.sin_addr);
        
        for(int i=0; i<50; i++) {
            if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
                send(sock, msg.c_str(), msg.length(), 0);
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        CLOSE_SOCK(sock);
    }

    std::string receiveData() {
        int server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd < 0) return "";
        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
        
        struct sockaddr_in address;
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);
        
        if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) { CLOSE_SOCK(server_fd); return ""; }
        if (listen(server_fd, 3) < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        int new_socket = accept(server_fd, nullptr, nullptr);
        if (new_socket < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        char buffer[4096] = {0};
        recv(new_socket, buffer, 4096, 0);
        std::string result(buffer);
        
        CLOSE_SOCK(new_socket);
        CLOSE_SOCK(server_fd);
        return result;
    }
};

"""

class CppCodeGenerator:
    @staticmethod
    def _escape_string(value: str) -> str:
        res = []
        for ch in value:
            if ch == "\n": res.append("\\n")
            elif ch == "\t": res.append("\\t")
            elif ch == '"': res.append('\\"')
            elif ch == "\\": res.append("\\\\")
            else: res.append(ch)
        return "".join(res)

    def _translate_expression(self, node: Optional[ASTNode]) -> str:
        if node is None: return "0"
        if isinstance(node, NumberExpr): return node.value
        if isinstance(node, StringExpr): return f'"{self._escape_string(node.value)}"'
        if isinstance(node, IdentifierExpr): return node.name
        if isinstance(node, UnaryExpr): return f"({node.op}{self._translate_expression(node.operand)})"
        if isinstance(node, BinaryExpr):
            return f"({self._translate_expression(node.left)} {node.op} {self._translate_expression(node.right)})"
        
        if isinstance(node, NewExpr):
            args = ", ".join(self._translate_expression(a) for a in node.arguments)
            return f"std::make_shared<{node.class_name}>({args})"
        if isinstance(node, ThisExpr): return "this"
        if isinstance(node, PropertyAccess):
            return f"{self._translate_expression(node.object)}->{node.property_name}"
        if isinstance(node, MethodCall):
            args = ", ".join(self._translate_expression(a) for a in node.arguments)
            return f"{self._translate_expression(node.object)}->{node.method_name}({args})"
        
        if isinstance(node, CChannelExpr):
            ip = self._translate_expression(node.ip)
            port = self._translate_expression(node.port)
            return f"std::make_shared<MiniParChannel>({ip}, {port})"
        if isinstance(node, ReceiveExpr):
            return f"{self._translate_expression(node.channel)}->receiveData()"

        # Array e Matrizes
        if isinstance(node, ListLiteral):
            elems = ", ".join(self._translate_expression(e) for e in node.elements)
            return f"std::vector{{{elems}}}"
        if isinstance(node, MatrixCreateExpr):
            r = self._translate_expression(node.rows)
            c = self._translate_expression(node.cols)
            v = self._translate_expression(node.init_value)
            return f"__make_matrix({r}, {c}, {v})"
        if isinstance(node, IndexExpr):
            obj = self._translate_expression(node.object)
            idx = self._translate_expression(node.index)
            return f"{obj}[{idx}]"

        return "0"

    def _translate_statement(self, node: Optional[ASTNode], indent: str = "") -> str:
        if node is None: return ""
        if isinstance(node, VarDecl):
            expr = self._translate_expression(node.init_value) if node.init_value else "0"
            return f"{indent}auto {node.name} = {expr};\n"
        if isinstance(node, Assignment):
            return f"{indent}{node.name} = {self._translate_expression(node.value)};\n"
        if isinstance(node, PropertyAssign):
            obj = self._translate_expression(node.object)
            return f"{indent}{obj}->{node.property_name} = {self._translate_expression(node.value)};\n"
        if isinstance(node, IndexAssign):
            tgt = self._translate_expression(node.target)
            return f"{indent}{tgt} = {self._translate_expression(node.value)};\n"
        
        if isinstance(node, MethodCall):
            return f"{indent}{self._translate_expression(node)};\n"
        if isinstance(node, ReturnStmt):
            val = self._translate_expression(node.value) if node.value else ""
            return f"{indent}return {val};\n"
        
        if isinstance(node, SendStmt):
            chan = self._translate_expression(node.channel)
            msg = self._translate_expression(node.message)
            return f"{indent}{chan}->sendData(__to_string({msg}));\n"

        if isinstance(node, PrintStmt):
            parts = [f" << {self._translate_expression(a)}" for a in node.arguments]
            sep = ' << " "'
            return f"{indent}std::cout{sep.join(parts)} << std::endl;\n"
        if isinstance(node, SeqBlock):
            lines = [f"{indent}{{\n"]
            for stmt in node.statements: lines.append(self._translate_statement(stmt, indent + "    "))
            lines.append(f"{indent}}}\n")
            return "".join(lines)
        if isinstance(node, ParBlock):
            lines = [f"{indent}{{\n", f"{indent}    std::vector<std::thread> __m_thr;\n"]
            for stmt in node.statements:
                lines.append(f"{indent}    __m_thr.emplace_back([&]() {{\n{self._translate_statement(stmt, indent + '        ')}{indent}    }});\n")
            lines.append(f"{indent}    for (auto& t : __m_thr) t.join();\n{indent}}}\n")
            return "".join(lines)
        if isinstance(node, WhileStmt):
            res = f"{indent}while ({self._translate_expression(node.condition)})\n"
            res += self._translate_statement(node.body, indent if isinstance(node.body, (SeqBlock, ParBlock)) else indent + "    ")
            return res
        if isinstance(node, IfStmt):
            res = f"{indent}if ({self._translate_expression(node.condition)})\n"
            res += self._translate_statement(node.then_branch, indent if isinstance(node.then_branch, (SeqBlock, ParBlock)) else indent + "    ")
            if node.else_branch:
                res = res.rstrip() + f"\n{indent}else\n"
                if isinstance(node.else_branch, IfStmt):
                    res = res.rstrip() + " " + self._translate_statement(node.else_branch, indent).lstrip()
                else:
                    res += self._translate_statement(node.else_branch, indent if isinstance(node.else_branch, (SeqBlock, ParBlock)) else indent + "    ")
            return res
        return ""

    def generate(self, program: Program, output_name: str) -> None:
        cpp_code = _CPP_HEADER
        
        for node in program.statements:
            if isinstance(node, ClassDecl):
                cpp_code += f"class {node.name}" + (f" : public {node.superclass}" if node.superclass else "") + " {\npublic:\n"
                for attr in node.attributes:
                    init = self._translate_expression(attr.init_value) if attr.init_value else "0"
                    cpp_code += f"    double {attr.name} = {init};\n"
                for method in node.methods:
                    params = ", ".join(f"auto {p}" for p in method.params)
                    cpp_code += f"    auto {method.name}({params}) {{\n"
                    if isinstance(method.body, SeqBlock):
                        for stmt in method.body.statements: cpp_code += self._translate_statement(stmt, "        ")
                    else: cpp_code += self._translate_statement(method.body, "        ")
                    cpp_code += "    }\n"
                cpp_code += "};\n\n"

        cpp_code += "int main() {\n    #ifdef _WIN32\n        WSADATA wsa;\n        WSAStartup(MAKEWORD(2,2), &wsa);\n    #endif\n\n"
        for node in program.statements:
            if not isinstance(node, ClassDecl):
                if isinstance(node, SeqBlock):
                    for stmt in node.statements: cpp_code += self._translate_statement(stmt, "    ")
                else: cpp_code += self._translate_statement(node, "    ")
        cpp_code += "\n    return 0;\n}\n"

        os.makedirs("output", exist_ok=True)
        cpp_path = os.path.join("output", f"{output_name}.cpp")
        exe_path = os.path.join("output", f"{output_name}.exe")

        with open(cpp_path, "w", encoding="utf-8") as f: f.write(cpp_code)
        
        print("[CODEGEN] Compilando via g++ com -std=c++20 e -O3...")
        result = subprocess.run(["g++", "-std=c++20", "-O3", cpp_path, "-o", exe_path, "-pthread", "-lws2_32"])
        if result.returncode == 0: print(f"[SUCESSO] Executavel: {exe_path}")
        else: print("[ERRO] Falha na compilacao.", file=sys.stderr)