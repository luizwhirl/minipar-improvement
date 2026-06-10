#include "codegen.h"
#include <iostream>
#include <fstream>
#include <cstdlib>

using namespace std;

// 1. A função que percorre a Árvore (AST) e traduz para C++
string CppCodeGenerator::translateNode(shared_ptr<ASTNode> node) {
    if (!node) return "";

    // Se encontrarmos um bloco SEQ, ele vira o nosso 'int main()' do C++
    if (auto seqBlock = dynamic_pointer_cast<SeqBlock>(node)) {
        string code = "int main() {\n";
        
        // Inicialização de Sockets para o Windows (necessário para o c_channel)
        code += "    #ifdef _WIN32\n";
        code += "        WSADATA wsa;\n";
        code += "        WSAStartup(MAKEWORD(2,2), &wsa);\n";
        code += "    #endif\n\n";

        // Traduz as instruções que estão dentro do 'seq'
        for (auto& stmt : seqBlock->statements) {
            // Se for uma declaração de variável (var a;)
            if (auto varDecl = dynamic_pointer_cast<VarDecl>(stmt)) {
                code += "    auto " + varDecl->name + " = 0;\n"; 
            }
        }

        code += "\n    return 0;\n";
        code += "}\n";
        
        return code;
    }

    return "";
}

// 2. A função principal que escreve o arquivo .cpp e chama o GCC
void CppCodeGenerator::generate(shared_ptr<Program> program, const string& outputName) {
    string cppCode = "";

    // Injetar bibliotecas base do C++ no código gerado
    cppCode += "#include <iostream>\n";
    cppCode += "#include <string>\n";
    cppCode += "#include <vector>\n";
    cppCode += "#include <thread>\n";
    cppCode += "#include <memory>\n";

    // Injetar infraestrutura de Sockets para o c_channel
    cppCode += "#ifdef _WIN32\n";
    cppCode += "  #include <winsock2.h>\n";
    cppCode += "  #pragma comment(lib, \"ws2_32.lib\")\n";
    cppCode += "#else\n";
    cppCode += "  #include <sys/socket.h>\n";
    cppCode += "  #include <arpa/inet.h>\n";
    cppCode += "  #include <unistd.h>\n";
    cppCode += "#endif\n\n";

    // Classe auxiliar de rede
    cppCode += "class MiniParChannel {\n";
    cppCode += "public:\n";
    cppCode += "    static void sendData(std::string ip, int port, std::string msg) {\n";
    cppCode += "        // Lógica TCP aqui\n";
    cppCode += "    }\n";
    cppCode += "    static std::string receiveData(int port) {\n";
    cppCode += "        return \"\";\n";
    cppCode += "    }\n";
    cppCode += "};\n\n";

    // Traduzir a AST (Aqui ele chama o translateNode)
    for (auto& node : program->statements) {
        cppCode += translateNode(node);
    }

    // Salvar o código gerado em um arquivo físico
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

    // A CORREÇÃO: g++ com flags de otimização, suporte a threads e link do Winsock do Windows
    cout << "[CODEGEN] Invocando o compilador g++ com otimizacao -O3..." << endl;
    string compileCommand = "g++ -O3 " + cppPath + " -o " + exePath + " -pthread -lws2_32";
    
    int result = system(compileCommand.c_str());

    if (result == 0) {
        cout << "[SUCESSO] Executavel gerado: " << exePath << endl;
    } else {
        cerr << "[ERRO] Falha na compilacao do g++." << endl;
    }
}