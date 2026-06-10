"""
parser.py — Analisador Sintático do compilador MiniPar
"""
from __future__ import annotations
import sys
from typing import List

from lexer import Token, TokenType
from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt,
    SeqBlock, ParBlock, BinaryExpr, UnaryExpr,
    NumberExpr, StringExpr, IdentifierExpr,
)


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------ #
    # Helpers internos                                                     #
    # ------------------------------------------------------------------ #

    def _peek(self) -> Token:
        if self._pos >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if self._pos < len(self._tokens):
            self._pos += 1
        return token

    def _match(self, token_type: TokenType) -> bool:
        if self._peek().type == token_type:
            self._advance()
            return True
        return False

    def _consume(self, token_type: TokenType, err_msg: str) -> Token:
        if self._peek().type == token_type:
            return self._advance()
        tok = self._peek()
        print(
            f"[ERRO SINTATICO] Linha {tok.line}: {err_msg} "
            f"(Encontrado: {tok.lexeme!r})",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Parsing de declarações                                               #
    # ------------------------------------------------------------------ #

    def _parse_var_decl(self) -> ASTNode:
        node = VarDecl(name="")
        node.line = self._peek().line
        node.name = self._consume(TokenType.IDENTIFIER, "Esperado nome da variavel").lexeme
        if self._match(TokenType.ASSIGN):
            node.init_value = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Esperado ';' apos declaracao de variavel")
        return node

    def _parse_assignment(self) -> ASTNode:
        node = Assignment(name="", value=None)
        node.line = self._peek().line
        node.name = self._consume(TokenType.IDENTIFIER, "Esperado nome da variavel").lexeme
        self._consume(TokenType.ASSIGN, "Esperado '=' em atribuicao")
        node.value = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Esperado ';' apos atribuicao")
        return node

    def _parse_print_stmt(self) -> ASTNode:
        node = PrintStmt()
        node.line = self._peek().line
        self._consume(TokenType.LPAREN, "Esperado '(' apos print")
        if self._peek().type != TokenType.RPAREN:
            node.arguments.append(self._parse_expression())
            while self._match(TokenType.COMMA):
                node.arguments.append(self._parse_expression())
        self._consume(TokenType.RPAREN, "Esperado ')' apos argumentos do print")
        self._consume(TokenType.SEMICOLON, "Esperado ';' apos print")
        return node

    def _parse_seq_block(self) -> ASTNode:
        node = SeqBlock()
        self._consume(TokenType.LBRACE, "Esperado '{' para iniciar bloco SEQ")
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            node.statements.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "Esperado '}' para fechar bloco SEQ")
        return node

    def _parse_par_block(self) -> ASTNode:
        node = ParBlock()
        self._consume(TokenType.LBRACE, "Esperado '{' para iniciar bloco PAR")
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            node.statements.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "Esperado '}' para fechar bloco PAR")
        return node

    def _parse_statement(self) -> ASTNode:
        if self._match(TokenType.VAR):
            return self._parse_var_decl()
        if self._match(TokenType.SEQ):
            return self._parse_seq_block()
        if self._match(TokenType.PAR):
            return self._parse_par_block()
        if self._match(TokenType.PRINT):
            return self._parse_print_stmt()

        # Atribuição: IDENTIFIER seguido de '='
        if (self._peek().type == TokenType.IDENTIFIER
                and self._pos + 1 < len(self._tokens)
                and self._tokens[self._pos + 1].type == TokenType.ASSIGN):
            return self._parse_assignment()

        tok = self._peek()
        print(
            f"[ERRO SINTATICO] Linha {tok.line}: Instrucao nao reconhecida: {tok.lexeme!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Parsing de expressões (precedência: + - > * / > unário > primário)  #
    # ------------------------------------------------------------------ #

    def _parse_expression(self) -> ASTNode:
        return self._parse_term()

    def _parse_term(self) -> ASTNode:
        expr = self._parse_factor()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            node = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_factor())
            node.line = op_tok.line
            expr = node
        return expr

    def _parse_factor(self) -> ASTNode:
        expr = self._parse_unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH):
            op_tok = self._advance()
            node = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_unary())
            node.line = op_tok.line
            expr = node
        return expr

    def _parse_unary(self) -> ASTNode:
        if self._peek().type in (TokenType.MINUS, TokenType.PLUS):
            op_tok = self._advance()
            node = UnaryExpr(op=op_tok.lexeme, operand=self._parse_unary())
            node.line = op_tok.line
            return node
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._peek()

        if self._match(TokenType.NUMBER):
            node = NumberExpr(value=self._tokens[self._pos - 1].lexeme)
            node.line = self._tokens[self._pos - 1].line
            return node

        if self._match(TokenType.STRING_LITERAL):
            node = StringExpr(value=self._tokens[self._pos - 1].lexeme)
            node.line = self._tokens[self._pos - 1].line
            return node

        if self._match(TokenType.IDENTIFIER):
            node = IdentifierExpr(name=self._tokens[self._pos - 1].lexeme)
            node.line = self._tokens[self._pos - 1].line
            return node

        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')' apos expressao")
            return expr

        print(
            f"[ERRO SINTATICO] Linha {tok.line}: Expressao esperada "
            f"(Encontrado: {tok.lexeme!r})",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Ponto de entrada                                                     #
    # ------------------------------------------------------------------ #

    def parse(self) -> Program:
        prog = Program()
        while self._peek().type != TokenType.END_OF_FILE:
            stmt = self._parse_statement()
            if stmt:
                prog.statements.append(stmt)
        return prog
