#include "parser.h"
#include <iostream>

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
    exit(1); // Aborta em caso de erro fatal
}

shared_ptr<ASTNode> Parser::parseVarDecl() {
    auto varDecl = make_shared<VarDecl>();
    varDecl->line = peek().line;
    varDecl->name = consume(TokenType::IDENTIFIER, "Esperado nome da variavel").lexeme;
    consume(TokenType::SEMICOLON, "Esperado ';' apos declaracao de variavel");
    return varDecl;
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

shared_ptr<ASTNode> Parser::parseStatement() {
    if (match(TokenType::VAR)) return parseVarDecl();
    if (match(TokenType::SEQ)) return parseSeqBlock();
    
    // Tratamento de fallback provisório para pular tokens não mapeados e evitar loop infinito no esqueleto
    cerr << "[AVISO] Ignorando instrucao nao mapeada no esqueleto: " << advance().lexeme << "\n";
    return nullptr; 
}

shared_ptr<Program> Parser::parse() {
    auto prog = make_shared<Program>();
    while (peek().type != TokenType::END_OF_FILE) {
        auto stmt = parseStatement();
        if (stmt) prog->statements.push_back(stmt);
    }
    return prog;
}