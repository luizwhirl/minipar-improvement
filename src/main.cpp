#include <iostream>
#include <fstream>
#include <sstream>
#include <memory>
#include "lexer.h"      // <-- Descomentado!
#include "parser.h"     // <-- Descomentado!
#include "semantic.h"
#include "codegen.h"
#include "ast.h"

using namespace std;

int main(int argc, char* argv[]) {
    if (argc < 2) {
        cout << "Uso: minipar_compiler <arquivo_fonte.minipar> [nome_saida]" << endl;
        return 1;
    }

    string sourcePath = argv[1];
    string outputName = (argc > 2) ? argv[2] : "programa_compilado";

    cout << "=== Compilador MiniPar 2026.1 (C++ Version) ===" << endl;

    // 1. Ler o arquivo fonte
    ifstream file(sourcePath);
    if (!file.is_open()) {
        cerr << "[ERRO] Arquivo nao encontrado: " << sourcePath << endl;
        return 1;
    }
    stringstream buffer;
    buffer << file.rdbuf();
    string sourceCode = buffer.str();

    // 2. Análise Léxica e Sintática REAIS (lendo o arquivo teste.minipar)
    cout << "[Fase 1] Analise Lexica e Sintatica..." << endl;
    Lexer lexer(sourceCode);
    auto tokens = lexer.tokenize();
    Parser parser(tokens);
    auto program = parser.parse(); 

    // 3. Análise Semântica
    cout << "[Fase 2] Analise Semantica e Tabela de Simbolos..." << endl;
    SemanticAnalyzer semantic;
    if (!semantic.analyze(program)) {
        cerr << "[ERRO] Falha na Analise Semantica. Compilacao abortada." << endl;
        return 1;
    }

    // 4. Geração de Código e GCC
    cout << "[Fase 3] Transpilacao e Chamada do GCC (-O3)..." << endl;
    CppCodeGenerator codegen;
    codegen.generate(program, outputName);

    cout << "=== Processo Finalizado ===" << endl;
    return 0;
}