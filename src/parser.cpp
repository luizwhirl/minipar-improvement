#include "parser.h"
#include <iostream>
#include <cstdlib>

using namespace std;

Parser::Parser(const vector<Token>& tokenList) : tokens(tokenList) {}

Token Parser::peek() {
    if (pos >= tokens.size()) return tokens.back();
    return tokens[pos];
}

Token Parser::advance() {
    if (pos < tokens.size()) pos++;
    return tokens[pos - 1];
}

bool Parser::match(TokenType type) {
    if (peek().type == type) {
        advance();
        return true;
    }
    return false;
}

Token Parser::consume(TokenType type, const string& errMsg) {
    if (peek().type == type) return advance();
    cerr << "[ERRO SINTATICO] Linha " << peek().line << ": " << errMsg << " (Encontrado: " << peek().lexeme << ")\n";
    exit(1);
}

shared_ptr<ASTNode> Parser::parseVarDecl() {
    auto varDecl = make_shared<VarDecl>();
    varDecl->line = peek().line;
    varDecl->name = consume(TokenType::IDENTIFIER, "Esperado nome da variavel").lexeme;
    if (match(TokenType::ASSIGN)) {
        varDecl->initValue = parseExpression();
    }
    consume(TokenType::SEMICOLON, "Esperado ';' apos declaracao de variavel");
    return varDecl;
}

shared_ptr<ASTNode> Parser::parseAssignment() {
    auto assignment = make_shared<Assignment>();
    assignment->line = peek().line;
    assignment->name = consume(TokenType::IDENTIFIER, "Esperado nome da variavel").lexeme;
    consume(TokenType::ASSIGN, "Esperado '=' em atribuicao");
    assignment->value = parseExpression();
    consume(TokenType::SEMICOLON, "Esperado ';' apos atribuicao");
    return assignment;
}

shared_ptr<ASTNode> Parser::parsePrintStmt() {
    auto printStmt = make_shared<PrintStmt>();
    printStmt->line = peek().line;
    consume(TokenType::LPAREN, "Esperado '(' apos print");
    if (peek().type != TokenType::RPAREN) {
        do {
            printStmt->arguments.push_back(parseExpression());
        } while (match(TokenType::COMMA));
    }
    consume(TokenType::RPAREN, "Esperado ')' apos argumentos do print");
    consume(TokenType::SEMICOLON, "Esperado ';' apos print");
    return printStmt;
}

shared_ptr<ASTNode> Parser::parseSeqBlock() {
    auto seq = make_shared<SeqBlock>();
    consume(TokenType::LBRACE, "Esperado '{' para iniciar bloco SEQ");
    while (peek().type != TokenType::RBRACE && peek().type != TokenType::END_OF_FILE) {
        seq->statements.push_back(parseStatement());
    }
    consume(TokenType::RBRACE, "Esperado '}' para fechar bloco SEQ");
    return seq;
}

shared_ptr<ASTNode> Parser::parseParBlock() {
    auto par = make_shared<ParBlock>();
    consume(TokenType::LBRACE, "Esperado '{' para iniciar bloco PAR");
    while (peek().type != TokenType::RBRACE && peek().type != TokenType::END_OF_FILE) {
        par->statements.push_back(parseStatement());
    }
    consume(TokenType::RBRACE, "Esperado '}' para fechar bloco PAR");
    return par;
}

shared_ptr<ASTNode> Parser::parseStatement() {
    if (match(TokenType::VAR)) return parseVarDecl();
    if (match(TokenType::SEQ)) return parseSeqBlock();
    if (match(TokenType::PAR)) return parseParBlock();
    if (match(TokenType::PRINT)) return parsePrintStmt();
    if (peek().type == TokenType::IDENTIFIER && pos + 1 < tokens.size() && tokens[pos + 1].type == TokenType::ASSIGN) {
        return parseAssignment();
    }

    cerr << "[ERRO SINTATICO] Linha " << peek().line << ": Instrucao nao reconhecida: " << peek().lexeme << "\n";
    exit(1);
}

shared_ptr<ASTNode> Parser::parseExpression() {
    return parseTerm();
}

shared_ptr<ASTNode> Parser::parseTerm() {
    auto expr = parseFactor();
    while (peek().type == TokenType::PLUS || peek().type == TokenType::MINUS) {
        Token op = advance();
        auto binary = make_shared<BinaryExpr>();
        binary->line = op.line;
        binary->op = op.lexeme;
        binary->left = expr;
        binary->right = parseFactor();
        expr = binary;
    }
    return expr;
}

shared_ptr<ASTNode> Parser::parseFactor() {
    auto expr = parseUnary();
    while (peek().type == TokenType::STAR || peek().type == TokenType::SLASH) {
        Token op = advance();
        auto binary = make_shared<BinaryExpr>();
        binary->line = op.line;
        binary->op = op.lexeme;
        binary->left = expr;
        binary->right = parseUnary();
        expr = binary;
    }
    return expr;
}

shared_ptr<ASTNode> Parser::parseUnary() {
    if (peek().type == TokenType::MINUS || peek().type == TokenType::PLUS) {
        Token op = advance();
        auto unary = make_shared<UnaryExpr>();
        unary->line = op.line;
        unary->op = op.lexeme;
        unary->operand = parseUnary();
        return unary;
    }
    return parsePrimary();
}

shared_ptr<ASTNode> Parser::parsePrimary() {
    if (match(TokenType::NUMBER)) {
        auto number = make_shared<NumberExpr>();
        number->line = tokens[pos - 1].line;
        number->value = tokens[pos - 1].lexeme;
        return number;
    }
    if (match(TokenType::STRING_LITERAL)) {
        auto text = make_shared<StringExpr>();
        text->line = tokens[pos - 1].line;
        text->value = tokens[pos - 1].lexeme;
        return text;
    }
    if (match(TokenType::IDENTIFIER)) {
        auto ident = make_shared<IdentifierExpr>();
        ident->line = tokens[pos - 1].line;
        ident->name = tokens[pos - 1].lexeme;
        return ident;
    }
    if (match(TokenType::LPAREN)) {
        auto expr = parseExpression();
        consume(TokenType::RPAREN, "Esperado ')' apos expressao");
        return expr;
    }

    cerr << "[ERRO SINTATICO] Linha " << peek().line << ": Expressao esperada (Encontrado: " << peek().lexeme << ")\n";
    exit(1);
}

shared_ptr<Program> Parser::parse() {
    auto prog = make_shared<Program>();
    while (peek().type != TokenType::END_OF_FILE) {
        auto stmt = parseStatement();
        if (stmt) prog->statements.push_back(stmt);
    }
    return prog;
}
