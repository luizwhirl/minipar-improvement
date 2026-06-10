#include "codegen.h"
#include <iostream>
#include <fstream>
#include <cstdlib>

using namespace std;

string CppCodeGenerator::escapeString(const string& value) {
    string escaped = "";
    for (char c : value) {
        switch (c) {
            case '\n': escaped += "\\n"; break;
            case '\t': escaped += "\\t"; break;
            case '"': escaped += "\\\""; break;
            case '\\': escaped += "\\\\"; break;
            default: escaped += c; break;
        }
    }
    return escaped;
}

string CppCodeGenerator::translateExpression(shared_ptr<ASTNode> node) {
    if (!node) return "0";
    if (auto number = dynamic_pointer_cast<NumberExpr>(node)) return number->value;
    if (auto text = dynamic_pointer_cast<StringExpr>(node)) return "\"" + escapeString(text->value) + "\"";
    if (auto ident = dynamic_pointer_cast<IdentifierExpr>(node)) return ident->name;
    if (auto unary = dynamic_pointer_cast<UnaryExpr>(node)) {
        return "(" + unary->op + translateExpression(unary->operand) + ")";
    }
    if (auto binary = dynamic_pointer_cast<BinaryExpr>(node)) {
        return "(" + translateExpression(binary->left) + " " + binary->op + " " + translateExpression(binary->right) + ")";
    }
    return "0";
}

string CppCodeGenerator::translateStatement(shared_ptr<ASTNode> node, const string& indent) {
    if (!node) return "";

    if (auto varDecl = dynamic_pointer_cast<VarDecl>(node)) {
        return indent + "auto " + varDecl->name + " = " + translateExpression(varDecl->initValue) + ";\n";
    }
    if (auto assignment = dynamic_pointer_cast<Assignment>(node)) {
        return indent + assignment->name + " = " + translateExpression(assignment->value) + ";\n";
    }
    if (auto printStmt = dynamic_pointer_cast<PrintStmt>(node)) {
        string code = indent + "std::cout";
        for (size_t i = 0; i < printStmt->arguments.size(); i++) {
            if (i > 0) code += " << \" \"";
            code += " << " + translateExpression(printStmt->arguments[i]);
        }
        code += " << std::endl;\n";
        return code;
    }
    if (auto seqBlock = dynamic_pointer_cast<SeqBlock>(node)) {
        string code = indent + "{\n";
        for (auto& stmt : seqBlock->statements) code += translateStatement(stmt, indent + "    ");
        code += indent + "}\n";
        return code;
    }
    if (auto parBlock = dynamic_pointer_cast<ParBlock>(node)) {
        string code = indent + "{\n";
        code += indent + "    std::vector<std::thread> __minipar_threads;\n";
        for (auto& stmt : parBlock->statements) {
            code += indent + "    __minipar_threads.emplace_back([&]() {\n";
            code += translateStatement(stmt, indent + "        ");
            code += indent + "    });\n";
        }
        code += indent + "    for (auto& __minipar_thread : __minipar_threads) __minipar_thread.join();\n";
        code += indent + "}\n";
        return code;
    }

    return "";
}

string CppCodeGenerator::translateNode(shared_ptr<ASTNode> node) {
    if (!node) return "";

    if (auto seqBlock = dynamic_pointer_cast<SeqBlock>(node)) {
        string code = "int main() {\n";
        code += "    #ifdef _WIN32\n";
        code += "        WSADATA wsa;\n";
        code += "        WSAStartup(MAKEWORD(2,2), &wsa);\n";
        code += "    #endif\n\n";

        for (auto& stmt : seqBlock->statements) {
            code += translateStatement(stmt, "    ");
        }

        code += "\n    return 0;\n";
        code += "}\n";
        return code;
    }

    return translateStatement(node, "");
}

void CppCodeGenerator::generate(shared_ptr<Program> program, const string& outputName) {
    string cppCode = "";

    cppCode += "#include <iostream>\n";
    cppCode += "#include <string>\n";
    cppCode += "#include <vector>\n";
    cppCode += "#include <thread>\n";
    cppCode += "#include <memory>\n";

    cppCode += "#ifdef _WIN32\n";
    cppCode += "  #include <winsock2.h>\n";
    cppCode += "  #pragma comment(lib, \"ws2_32.lib\")\n";
    cppCode += "#else\n";
    cppCode += "  #include <sys/socket.h>\n";
    cppCode += "  #include <arpa/inet.h>\n";
    cppCode += "  #include <unistd.h>\n";
    cppCode += "#endif\n\n";

    cppCode += "class MiniParChannel {\n";
    cppCode += "public:\n";
    cppCode += "    static void sendData(std::string ip, int port, std::string msg) {\n";
    cppCode += "        // Logica TCP aqui\n";
    cppCode += "    }\n";
    cppCode += "    static std::string receiveData(int port) {\n";
    cppCode += "        return \"\";\n";
    cppCode += "    }\n";
    cppCode += "};\n\n";

    for (auto& node : program->statements) {
        cppCode += translateNode(node);
    }

    string cppPath = "output/" + outputName + ".cpp";
    string exePath = "output/" + outputName + ".exe";

    ofstream outFile(cppPath);
    if (outFile.is_open()) {
        outFile << cppCode;
        outFile.close();
        cout << "[CODEGEN] Codigo C++ gerado com sucesso em: " << cppPath << endl;
    } else {
        cerr << "[ERRO] Nao foi possivel criar o arquivo .cpp!" << endl;
        return;
    }

    cout << "[CODEGEN] Invocando o compilador g++ com otimizacao -O3..." << endl;
    string compileCommand = "g++ -O3 " + cppPath + " -o " + exePath + " -pthread -lws2_32";

    int result = system(compileCommand.c_str());

    if (result == 0) {
        cout << "[SUCESSO] Executavel gerado: " << exePath << endl;
    } else {
        cerr << "[ERRO] Falha na compilacao do g++." << endl;
    }
}
