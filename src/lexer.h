#pragma once
#include <string>
#include <vector>

// Tipos de Tokens suportados pela MiniPar
enum class TokenType {
    IDENTIFIER, NUMBER, STRING_LITERAL,
    CLASS, EXTENDS, NEW, FUNC, VAR, 
    IF, ELSE, WHILE, RETURN, 
    SEQ, PAR, C_CHANNEL, SEND, RECEIVE,
    PLUS, MINUS, STAR, SLASH, ASSIGN, EQ, NEQ,
    LPAREN, RPAREN, LBRACE, RBRACE, DOT, SEMICOLON, COMMA,
    END_OF_FILE, UNKNOWN
};

struct Token {
    TokenType type;
    std::string lexeme;
    int line;
    int col;
};

class Lexer {
private:
    std::string source;
    int pos = 0;
    int line = 1;
    int col = 1;

    char peek();
    char advance();
    void skipWhitespaceAndComments();
    Token createToken(TokenType type, std::string lexeme);

public:
    Lexer(const std::string& sourceCode);
    std::vector<Token> tokenize();
};