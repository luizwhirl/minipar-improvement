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
        if (isspace(static_cast<unsigned char>(c))) {
            advance();
        } else if (c == '#') {
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
        {"if", TokenType::IF}, {"else", TokenType::ELSE}, {"while", TokenType::WHILE},
        {"return", TokenType::RETURN}, {"func", TokenType::FUNC}, {"var", TokenType::VAR},
        {"print", TokenType::PRINT},
        {"c_channel", TokenType::C_CHANNEL}, {"send", TokenType::SEND}, {"receive", TokenType::RECEIVE}
    };

    while (pos < source.length()) {
        skipWhitespaceAndComments();
        if (pos >= source.length()) break;

        char c = peek();

        if (isalpha(static_cast<unsigned char>(c)) || c == '_') {
            int startLine = line;
            int startCol = col;
            string ident = "";
            while (isalnum(static_cast<unsigned char>(peek())) || peek() == '_') ident += advance();

            if (keywords.count(ident)) tokens.push_back({keywords[ident], ident, startLine, startCol});
            else tokens.push_back({TokenType::IDENTIFIER, ident, startLine, startCol});
        }
        else if (isdigit(static_cast<unsigned char>(c))) {
            int startLine = line;
            int startCol = col;
            string num = "";
            while (isdigit(static_cast<unsigned char>(peek()))) num += advance();
            tokens.push_back({TokenType::NUMBER, num, startLine, startCol});
        }
        else if (c == '"') {
            int startLine = line;
            int startCol = col;
            advance();
            string text = "";

            while (peek() != '"' && peek() != '\0') {
                if (peek() == '\\') {
                    advance();
                    char escaped = advance();
                    switch (escaped) {
                        case 'n': text += '\n'; break;
                        case 't': text += '\t'; break;
                        case '"': text += '"'; break;
                        case '\\': text += '\\'; break;
                        default: text += escaped; break;
                    }
                } else {
                    text += advance();
                }
            }

            if (peek() == '"') advance();
            tokens.push_back({TokenType::STRING_LITERAL, text, startLine, startCol});
        }
        else {
            int startLine = line;
            int startCol = col;
            char op = advance();
            switch (op) {
                case '+': tokens.push_back({TokenType::PLUS, "+", startLine, startCol}); break;
                case '-': tokens.push_back({TokenType::MINUS, "-", startLine, startCol}); break;
                case '*': tokens.push_back({TokenType::STAR, "*", startLine, startCol}); break;
                case '/': tokens.push_back({TokenType::SLASH, "/", startLine, startCol}); break;
                case '{': tokens.push_back({TokenType::LBRACE, "{", startLine, startCol}); break;
                case '}': tokens.push_back({TokenType::RBRACE, "}", startLine, startCol}); break;
                case '(': tokens.push_back({TokenType::LPAREN, "(", startLine, startCol}); break;
                case ')': tokens.push_back({TokenType::RPAREN, ")", startLine, startCol}); break;
                case ';': tokens.push_back({TokenType::SEMICOLON, ";", startLine, startCol}); break;
                case ',': tokens.push_back({TokenType::COMMA, ",", startLine, startCol}); break;
                case '.': tokens.push_back({TokenType::DOT, ".", startLine, startCol}); break;
                case '=':
                    if (peek() == '=') { advance(); tokens.push_back({TokenType::EQ, "==", startLine, startCol}); }
                    else tokens.push_back({TokenType::ASSIGN, "=", startLine, startCol});
                    break;
                case '!':
                    if (peek() == '=') { advance(); tokens.push_back({TokenType::NEQ, "!=", startLine, startCol}); }
                    else tokens.push_back({TokenType::UNKNOWN, string(1, op), startLine, startCol});
                    break;
                default: tokens.push_back({TokenType::UNKNOWN, string(1, op), startLine, startCol}); break;
            }
        }
    }
    tokens.push_back(createToken(TokenType::END_OF_FILE, ""));
    return tokens;
}
