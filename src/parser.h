#pragma once
#include "lexer.h"
#include "ast.h"
#include <cstddef>
#include <vector>
#include <memory>

class Parser {
private:
    std::vector<Token> tokens;
    std::size_t pos = 0;

    Token peek();
    Token advance();
    bool match(TokenType type);
    Token consume(TokenType type, const std::string& errMsg);

    std::shared_ptr<ASTNode> parseStatement();
    std::shared_ptr<ASTNode> parseVarDecl();
    std::shared_ptr<ASTNode> parseAssignment();
    std::shared_ptr<ASTNode> parsePrintStmt();
    std::shared_ptr<ASTNode> parseSeqBlock();
    std::shared_ptr<ASTNode> parseParBlock();
    std::shared_ptr<ASTNode> parseExpression();
    std::shared_ptr<ASTNode> parseTerm();
    std::shared_ptr<ASTNode> parseFactor();
    std::shared_ptr<ASTNode> parseUnary();
    std::shared_ptr<ASTNode> parsePrimary();

public:
    Parser(const std::vector<Token>& tokenList);
    std::shared_ptr<Program> parse();
};
