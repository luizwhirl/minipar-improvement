#include "lexer.h"
#include <cctype>
#include <unordered_map>

using namespace std;

Lexer::Lexer(const string& sourceCode) : source(sourceCode) {}

char Lexer::peek() {
    if (pos >= source.length()) return '\0';
    return source[pos];
}

char Lexer::advance() {
    char c = source[pos++];
    if (c == '\n') { line++; col = 1; } 
    else { col++; }
    return c;
}

void Lexer::skipWhitespaceAndComments() {
    while (pos < source.length()) {
        char c = peek();
        if (isspace(c)) {
            advance();
        } else if (c == '#') { // Comentário MiniPar
            while (peek() != '\n' && peek() != '\0') advance();
        } else {
            break;
        }
    }
}

Token Lexer::createToken(TokenType type, string lexeme) {
    return {type, lexeme, line, col};
}

vector<Token> Lexer::tokenize() {
    vector<Token> tokens;
    unordered_map<string, TokenType> keywords = {
        {"class", TokenType::CLASS}, {"extends", TokenType::EXTENDS},
        {"new", TokenType::NEW}, {"seq", TokenType::SEQ}, {"par", TokenType::PAR},
        {"if", TokenType::IF}, {"while", TokenType::WHILE}, {"var", TokenType::VAR},
        {"c_channel", TokenType::C_CHANNEL}, {"send", TokenType::SEND}, {"receive", TokenType::RECEIVE}
    };

    while (pos < source.length()) {
        skipWhitespaceAndComments();
        if (pos >= source.length()) break;

        char c = peek();

        if (isalpha(c) || c == '_') {
            string ident = "";
            while (isalnum(peek()) || peek() == '_') ident += advance();
            
            if (keywords.count(ident)) tokens.push_back(createToken(keywords[ident], ident));
            else tokens.push_back(createToken(TokenType::IDENTIFIER, ident));
        } 
        else if (isdigit(c)) {
            string num = "";
            while (isdigit(peek())) num += advance();
            tokens.push_back(createToken(TokenType::NUMBER, num));
        }
        else {
            char op = advance();
            switch (op) {
                case '{': tokens.push_back(createToken(TokenType::LBRACE, "{")); break;
                case '}': tokens.push_back(createToken(TokenType::RBRACE, "}")); break;
                case '(': tokens.push_back(createToken(TokenType::LPAREN, "(")); break;
                case ')': tokens.push_back(createToken(TokenType::RPAREN, ")")); break;
                case ';': tokens.push_back(createToken(TokenType::SEMICOLON, ";")); break;
                case '.': tokens.push_back(createToken(TokenType::DOT, ".")); break;
                case '=': 
                    if (peek() == '=') { advance(); tokens.push_back(createToken(TokenType::EQ, "==")); }
                    else tokens.push_back(createToken(TokenType::ASSIGN, "="));
                    break;
                default: tokens.push_back(createToken(TokenType::UNKNOWN, string(1, op))); break;
            }
        }
    }
    tokens.push_back(createToken(TokenType::END_OF_FILE, ""));
    return tokens;
}