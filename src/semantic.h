#pragma once
#include "ast.h"
#include <unordered_map>
#include <vector>
#include <string>

// Estrutura do Símbolo
struct Symbol {
    std::string name;
    std::string type;
};

class SemanticAnalyzer {
private:
    std::vector<std::unordered_map<std::string, Symbol>> scopes;
    bool hasErrors = false;

public:
    SemanticAnalyzer();
    void enterScope();
    void exitScope();
    void defineSymbol(const std::string& name, const std::string& type, int line);
    Symbol* lookup(const std::string& name);
    
    bool analyze(std::shared_ptr<Program> program);
    void validateNode(std::shared_ptr<ASTNode> node);
};