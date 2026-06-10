#include "semantic.h"
#include <iostream>

using namespace std;

SemanticAnalyzer::SemanticAnalyzer() {
    enterScope(); // Escopo Global
}

void SemanticAnalyzer::enterScope() {
    scopes.push_back(unordered_map<string, Symbol>());
}

void SemanticAnalyzer::exitScope() {
    if (scopes.size() > 1) scopes.pop_back();
}

void SemanticAnalyzer::defineSymbol(const string& name, const string& type, int line) {
    if (scopes.back().count(name)) {
        cerr << "[ERRO SEMANTICO] Linha " << line << ": Variavel '" << name << "' ja declarada neste escopo.\n";
        hasErrors = true;
    } else {
        scopes.back()[name] = {name, type};
    }
}

Symbol* SemanticAnalyzer::lookup(const string& name) {
    for (int i = scopes.size() - 1; i >= 0; i--) {
        if (scopes[i].count(name)) return &scopes[i][name];
    }
    return nullptr;
}

void SemanticAnalyzer::validateNode(shared_ptr<ASTNode> node) {
    if (!node) return;

    // RTTI (Run-Time Type Information) para descobrir qual é o nó
    if (auto varDecl = dynamic_pointer_cast<VarDecl>(node)) {
        defineSymbol(varDecl->name, "VAR", varDecl->line);
    } 
    else if (auto seqBlock = dynamic_pointer_cast<SeqBlock>(node)) {
        enterScope();
        for (auto& stmt : seqBlock->statements) validateNode(stmt);
        exitScope();
    }
}

bool SemanticAnalyzer::analyze(shared_ptr<Program> program) {
    for (auto& stmt : program->statements) {
        validateNode(stmt);
    }
    return !hasErrors;
}