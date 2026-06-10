#pragma once
#include <string>
#include <vector>
#include <memory>

// Superclasse de todos os nos da Arvore
struct ASTNode {
    virtual ~ASTNode() = default;
    int line = 1; // Para rastrear erros
};

// Declaracao de Variavel
struct VarDecl : public ASTNode {
    std::string type;
    std::string name;
    std::shared_ptr<ASTNode> initValue;
};

struct Assignment : public ASTNode {
    std::string name;
    std::shared_ptr<ASTNode> value;
};

struct PrintStmt : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> arguments;
};

struct NumberExpr : public ASTNode {
    std::string value;
};

struct StringExpr : public ASTNode {
    std::string value;
};

struct IdentifierExpr : public ASTNode {
    std::string name;
};

struct BinaryExpr : public ASTNode {
    std::string op;
    std::shared_ptr<ASTNode> left;
    std::shared_ptr<ASTNode> right;
};

struct UnaryExpr : public ASTNode {
    std::string op;
    std::shared_ptr<ASTNode> operand;
};

// Bloco Sequencial (SEQ)
struct SeqBlock : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> statements;
};

// Bloco Paralelo (PAR)
struct ParBlock : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> statements;
};

// No raiz do Programa
struct Program : public ASTNode {
    std::vector<std::shared_ptr<ASTNode>> statements;
};
