#pragma once
#include <string>
#include <vector>
#include <memory>

// Superclasse de todos os nós da Árvore
struct ASTNode {
    virtual ~ASTNode() = default;
    int line; // Para rastrear erros
};

// Declaração de Variável
struct VarDecl : public ASTNode {
    std::string type;
    std::string name;
    std::shared_ptr<ASTNode> initValue;
};

// Bloco Sequencial (SEQ)
struct SeqBlock : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> statements;
};

// Bloco Paralelo (PAR)
struct ParBlock : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> statements;
};

// Nó raiz do Programa
struct Program : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> statements;
};