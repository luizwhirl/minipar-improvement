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
    for (int i = static_cast<int>(scopes.size()) - 1; i >= 0; i--) {
        if (scopes[i].count(name)) return &scopes[i][name];
    }
    return nullptr;
}

void SemanticAnalyzer::validateNode(shared_ptr<ASTNode> node) {
    if (!node) return;

    if (auto varDecl = dynamic_pointer_cast<VarDecl>(node)) {
        defineSymbol(varDecl->name, "VAR", varDecl->line);
        validateNode(varDecl->initValue);
    }
    else if (auto assignment = dynamic_pointer_cast<Assignment>(node)) {
        if (!lookup(assignment->name)) {
            cerr << "[ERRO SEMANTICO] Linha " << assignment->line << ": Variavel '" << assignment->name << "' nao declarada.\n";
            hasErrors = true;
        }
        validateNode(assignment->value);
    }
    else if (auto printStmt = dynamic_pointer_cast<PrintStmt>(node)) {
        for (auto& arg : printStmt->arguments) validateNode(arg);
    }
    else if (auto ident = dynamic_pointer_cast<IdentifierExpr>(node)) {
        if (!lookup(ident->name)) {
            cerr << "[ERRO SEMANTICO] Linha " << ident->line << ": Variavel '" << ident->name << "' nao declarada.\n";
            hasErrors = true;
        }
    }
    else if (auto binary = dynamic_pointer_cast<BinaryExpr>(node)) {
        validateNode(binary->left);
        validateNode(binary->right);
    }
    else if (auto unary = dynamic_pointer_cast<UnaryExpr>(node)) {
        validateNode(unary->operand);
    }
    else if (auto seqBlock = dynamic_pointer_cast<SeqBlock>(node)) {
        enterScope();
        for (auto& stmt : seqBlock->statements) validateNode(stmt);
        exitScope();
    }
    else if (auto parBlock = dynamic_pointer_cast<ParBlock>(node)) {
        enterScope();
        for (auto& stmt : parBlock->statements) validateNode(stmt);
        exitScope();
    }
}

bool SemanticAnalyzer::analyze(shared_ptr<Program> program) {
    for (auto& stmt : program->statements) {
        validateNode(stmt);
    }
    return !hasErrors;
}
