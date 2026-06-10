"""
lexer.py — Analisador Léxico do compilador MiniPar
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class TokenType(Enum):
    IDENTIFIER     = auto()
    NUMBER         = auto()
    STRING_LITERAL = auto()

    # Palavras-chave
    CLASS     = auto()
    EXTENDS   = auto()
    NEW       = auto()
    FUNC      = auto()
    VAR       = auto()
    IF        = auto()
    ELSE      = auto()
    WHILE     = auto()
    RETURN    = auto()
    SEQ       = auto()
    PAR       = auto()
    C_CHANNEL = auto()
    SEND      = auto()
    RECEIVE   = auto()
    PRINT     = auto()

    # Operadores e pontuação
    PLUS      = auto()
    MINUS     = auto()
    STAR      = auto()
    SLASH     = auto()
    ASSIGN    = auto()
    EQ        = auto()
    NEQ       = auto()
    LPAREN    = auto()
    RPAREN    = auto()
    LBRACE    = auto()
    RBRACE    = auto()
    DOT       = auto()
    SEMICOLON = auto()
    COMMA     = auto()

    END_OF_FILE = auto()
    UNKNOWN     = auto()


KEYWORDS: dict[str, TokenType] = {
    "class":     TokenType.CLASS,
    "extends":   TokenType.EXTENDS,
    "new":       TokenType.NEW,
    "seq":       TokenType.SEQ,
    "par":       TokenType.PAR,
    "if":        TokenType.IF,
    "else":      TokenType.ELSE,
    "while":     TokenType.WHILE,
    "return":    TokenType.RETURN,
    "func":      TokenType.FUNC,
    "var":       TokenType.VAR,
    "print":     TokenType.PRINT,
    "c_channel": TokenType.C_CHANNEL,
    "send":      TokenType.SEND,
    "receive":   TokenType.RECEIVE,
}


@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.lexeme!r}, l{self.line}:c{self.col})"


class Lexer:
    def __init__(self, source_code: str) -> None:
        self._source = source_code
        self._pos = 0
        self._line = 1
        self._col = 1

    # ------------------------------------------------------------------ #
    # Helpers internos                                                     #
    # ------------------------------------------------------------------ #

    def _peek(self) -> str:
        if self._pos >= len(self._source):
            return "\0"
        return self._source[self._pos]

    def _advance(self) -> str:
        ch = self._source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _skip_whitespace_and_comments(self) -> None:
        while self._pos < len(self._source):
            ch = self._peek()
            if ch.isspace():
                self._advance()
            elif ch == "#":
                while self._peek() not in ("\n", "\0"):
                    self._advance()
            else:
                break

    def _make_token(self, token_type: TokenType, lexeme: str,
                    line: int, col: int) -> Token:
        return Token(token_type, lexeme, line, col)

    # ------------------------------------------------------------------ #
    # Tokenização                                                          #
    # ------------------------------------------------------------------ #

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self._pos < len(self._source):
            self._skip_whitespace_and_comments()
            if self._pos >= len(self._source):
                break

            ch = self._peek()
            start_line = self._line
            start_col = self._col

            # Identificadores e palavras-chave
            if ch.isalpha() or ch == "_":
                ident = ""
                while self._peek().isalnum() or self._peek() == "_":
                    ident += self._advance()
                ttype = KEYWORDS.get(ident, TokenType.IDENTIFIER)
                tokens.append(self._make_token(ttype, ident, start_line, start_col))

            # Números inteiros
            elif ch.isdigit():
                num = ""
                while self._peek().isdigit():
                    num += self._advance()
                tokens.append(self._make_token(TokenType.NUMBER, num, start_line, start_col))

            # String literal
            elif ch == '"':
                self._advance()  # consome a aspa de abertura
                text = ""
                while self._peek() not in ('"', "\0"):
                    if self._peek() == "\\":
                        self._advance()
                        escaped = self._advance()
                        escape_map = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
                        text += escape_map.get(escaped, escaped)
                    else:
                        text += self._advance()
                if self._peek() == '"':
                    self._advance()  # consome a aspa de fechamento
                tokens.append(self._make_token(TokenType.STRING_LITERAL, text, start_line, start_col))

            # Operadores e pontuação
            else:
                op = self._advance()
                single_map = {
                    "+": TokenType.PLUS,
                    "-": TokenType.MINUS,
                    "*": TokenType.STAR,
                    "/": TokenType.SLASH,
                    "{": TokenType.LBRACE,
                    "}": TokenType.RBRACE,
                    "(": TokenType.LPAREN,
                    ")": TokenType.RPAREN,
                    ";": TokenType.SEMICOLON,
                    ",": TokenType.COMMA,
                    ".": TokenType.DOT,
                }
                if op == "=":
                    if self._peek() == "=":
                        self._advance()
                        tokens.append(self._make_token(TokenType.EQ, "==", start_line, start_col))
                    else:
                        tokens.append(self._make_token(TokenType.ASSIGN, "=", start_line, start_col))
                elif op == "!":
                    if self._peek() == "=":
                        self._advance()
                        tokens.append(self._make_token(TokenType.NEQ, "!=", start_line, start_col))
                    else:
                        tokens.append(self._make_token(TokenType.UNKNOWN, op, start_line, start_col))
                elif op in single_map:
                    tokens.append(self._make_token(single_map[op], op, start_line, start_col))
                else:
                    tokens.append(self._make_token(TokenType.UNKNOWN, op, start_line, start_col))

        tokens.append(Token(TokenType.END_OF_FILE, "", self._line, self._col))
        return tokens
