#pragma once
#include "lexer.h"
#include "ast.h"
#include <vector>
#include <memory>

class Parser {
private:
    std::vector<Token> tokens;
    int pos = 0;

    Token peek();
    Token advance();
    bool match(TokenType type);
    Token consume(TokenType type, const std::string& errMsg);

    std::shared_ptr<ASTNode> parseStatement();
    std::shared_ptr<ASTNode> parseVarDecl();
    std::shared_ptr<ASTNode> parseSeqBlock();
    std::shared_ptr<ASTNode> parseParBlock();

public:
    Parser(const std::vector<Token>& tokenList);
    std::shared_ptr<Program> parse();
};