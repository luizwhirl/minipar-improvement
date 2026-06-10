from __future__ import annotations
import sys
from typing import List
from lexer import Token, TokenType
from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt, SeqBlock, ParBlock, 
    BinaryExpr, UnaryExpr, NumberExpr, StringExpr, IdentifierExpr, IfStmt, WhileStmt,
    ClassDecl, FuncDecl, ReturnStmt, MethodCall, PropertyAccess, PropertyAssign, NewExpr, ThisExpr,
    CChannelExpr, SendStmt, ReceiveExpr, ListLiteral, MatrixCreateExpr, IndexExpr, IndexAssign
)

class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token:
        if self._pos >= len(self._tokens): return self._tokens[-1]
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if self._pos < len(self._tokens): self._pos += 1
        return token

    def _match(self, token_type: TokenType) -> bool:
        if self._peek().type == token_type:
            self._advance()
            return True
        return False

    def _consume(self, token_type: TokenType, err_msg: str) -> Token:
        if self._peek().type == token_type: return self._advance()
        tok = self._peek()
        print(f"[ERRO SINTATICO] Linha {tok.line}: {err_msg} (Encontrado: {tok.lexeme!r})", file=sys.stderr)
        sys.exit(1)

    def _parse_var_decl(self) -> ASTNode:
        node = VarDecl(name="")
        node.line = self._peek().line
        node.name = self._consume(TokenType.IDENTIFIER, "Esperado nome da variavel").lexeme
        if self._match(TokenType.ASSIGN):
            node.init_value = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Esperado ';' apos declaracao de variavel")
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

    def _parse_send_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        self._consume(TokenType.LPAREN, "Esperado '(' apos send")
        channel = self._parse_expression()
        self._consume(TokenType.COMMA, "Esperado ',' entre canal e mensagem")
        message = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')'")
        self._consume(TokenType.SEMICOLON, "Esperado ';'")
        return SendStmt(channel=channel, message=message, line=line)

    def _parse_seq_block(self) -> ASTNode:
        node = SeqBlock()
        self._consume(TokenType.LBRACE, "Esperado '{' para iniciar bloco")
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            node.statements.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "Esperado '}' para fechar bloco")
        return node

    def _parse_par_block(self) -> ASTNode:
        node = ParBlock()
        self._consume(TokenType.LBRACE, "Esperado '{' para iniciar bloco PAR")
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            node.statements.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "Esperado '}' para fechar bloco PAR")
        return node

    def _parse_if_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        self._consume(TokenType.LPAREN, "Esperado '(' apos 'if'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')' apos condicao do 'if'")
        then_branch = self._parse_statement()
        else_branch = self._parse_statement() if self._match(TokenType.ELSE) else None
        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch, line=line)

    def _parse_while_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        self._consume(TokenType.LPAREN, "Esperado '(' apos 'while'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')' apos condicao")
        body = self._parse_statement()
        return WhileStmt(condition=condition, body=body, line=line)

    def _parse_class_decl(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        name = self._consume(TokenType.IDENTIFIER, "Esperado nome da classe").lexeme
        superclass = self._consume(TokenType.IDENTIFIER, "Esperado nome da superclasse").lexeme if self._match(TokenType.EXTENDS) else None
        self._consume(TokenType.LBRACE, "Esperado '{' na classe")
        attrs, methods = [], []
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            if self._match(TokenType.VAR): attrs.append(self._parse_var_decl())
            elif self._match(TokenType.FUNC): methods.append(self._parse_func_decl())
            else: self._consume(TokenType.UNKNOWN, "Esperado 'var' ou 'func' na definicao da classe")
        self._consume(TokenType.RBRACE, "Esperado '}' no fim da classe")
        return ClassDecl(name=name, superclass=superclass, attributes=attrs, methods=methods, line=line)

    def _parse_func_decl(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        name = self._consume(TokenType.IDENTIFIER, "Esperado nome da funcao").lexeme
        self._consume(TokenType.LPAREN, "Esperado '('")
        params = []
        if self._peek().type != TokenType.RPAREN:
            params.append(self._consume(TokenType.IDENTIFIER, "Esperado parametro").lexeme)
            while self._match(TokenType.COMMA):
                params.append(self._consume(TokenType.IDENTIFIER, "Esperado parametro").lexeme)
        self._consume(TokenType.RPAREN, "Esperado ')'")
        body = self._parse_seq_block()
        return FuncDecl(name=name, params=params, body=body, line=line)

    def _parse_return_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        value = None if self._peek().type == TokenType.SEMICOLON else self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Esperado ';'")
        return ReturnStmt(value=value, line=line)

    def _parse_statement(self) -> ASTNode:
        if self._match(TokenType.CLASS): return self._parse_class_decl()
        if self._match(TokenType.FUNC): return self._parse_func_decl()
        if self._match(TokenType.RETURN): return self._parse_return_stmt()
        if self._match(TokenType.VAR): return self._parse_var_decl()
        if self._match(TokenType.SEQ) or self._peek().type == TokenType.LBRACE: 
            if self._peek().type == TokenType.SEQ: self._advance()
            return self._parse_seq_block()
        if self._match(TokenType.PAR): return self._parse_par_block()
        if self._match(TokenType.PRINT): return self._parse_print_stmt()
        if self._match(TokenType.SEND): return self._parse_send_stmt()
        if self._match(TokenType.IF): return self._parse_if_stmt()
        if self._match(TokenType.WHILE): return self._parse_while_stmt()

        # Intercepta as expressões que podem sofrer atribuição (Identificadores, Propriedades e Arrays)
        if self._peek().type in (TokenType.IDENTIFIER, TokenType.THIS, TokenType.NEW, TokenType.RECEIVE, TokenType.C_CHANNEL, TokenType.MATRIX, TokenType.LBRACKET):
            expr = self._parse_expression()
            if self._match(TokenType.ASSIGN):
                val = self._parse_expression()
                self._consume(TokenType.SEMICOLON, "Esperado ';'")
                if isinstance(expr, IdentifierExpr): return Assignment(name=expr.name, value=val, line=expr.line)
                elif isinstance(expr, PropertyAccess): return PropertyAssign(object=expr.object, property_name=expr.property_name, value=val, line=expr.line)
                elif isinstance(expr, IndexExpr): return IndexAssign(target=expr, value=val, line=expr.line)
                else: sys.exit(print(f"[ERRO] Linha {expr.line}: Atribuicao invalida", file=sys.stderr) or 1)
            elif isinstance(expr, MethodCall):
                self._consume(TokenType.SEMICOLON, "Esperado ';'")
                return expr
            sys.exit(print(f"[ERRO] Linha {expr.line}: Instrucao ou expressao isolada invalida", file=sys.stderr) or 1)

        tok = self._peek()
        sys.exit(print(f"[ERRO SINTATICO] Linha {tok.line}: Instrucao nao reconhecida: {tok.lexeme!r}", file=sys.stderr) or 1)

    def _parse_expression(self) -> ASTNode:
        return self._parse_comparison()

    def _parse_comparison(self) -> ASTNode:
        expr = self._parse_term()
        while self._peek().type in (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op_tok = self._advance()
            node = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_term())
            node.line = op_tok.line
            expr = node
        return expr

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
        node = None

        if self._match(TokenType.MATRIX):
            line = tok.line
            self._consume(TokenType.LPAREN, "Esperado '(' apos matrix")
            rows = self._parse_expression()
            self._consume(TokenType.COMMA, "Esperado ','")
            cols = self._parse_expression()
            self._consume(TokenType.COMMA, "Esperado ','")
            init_val = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = MatrixCreateExpr(rows=rows, cols=cols, init_value=init_val, line=line)
        elif self._match(TokenType.LBRACKET):
            line = tok.line
            elements = []
            if self._peek().type != TokenType.RBRACKET:
                elements.append(self._parse_expression())
                while self._match(TokenType.COMMA): elements.append(self._parse_expression())
            self._consume(TokenType.RBRACKET, "Esperado ']'")
            node = ListLiteral(elements=elements, line=line)
        elif self._match(TokenType.C_CHANNEL):
            line = tok.line
            self._consume(TokenType.LPAREN, "Esperado '(' apos c_channel")
            ip = self._parse_expression()
            self._consume(TokenType.COMMA, "Esperado ',' entre ip e porta")
            port = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = CChannelExpr(ip=ip, port=port, line=line)
        elif self._match(TokenType.RECEIVE):
            line = tok.line
            self._consume(TokenType.LPAREN, "Esperado '(' apos receive")
            channel = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = ReceiveExpr(channel=channel, line=line)
        elif self._match(TokenType.NEW):
            line = tok.line
            class_name = self._consume(TokenType.IDENTIFIER, "Esperado nome da classe").lexeme
            self._consume(TokenType.LPAREN, "Esperado '('")
            args = []
            if self._peek().type != TokenType.RPAREN:
                args.append(self._parse_expression())
                while self._match(TokenType.COMMA): args.append(self._parse_expression())
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = NewExpr(class_name=class_name, arguments=args, line=line)
        elif self._match(TokenType.THIS):
            node = ThisExpr(line=tok.line)
        elif self._match(TokenType.NUMBER):
            node = NumberExpr(value=tok.lexeme, line=tok.line)
        elif self._match(TokenType.STRING_LITERAL):
            node = StringExpr(value=tok.lexeme, line=tok.line)
        elif self._match(TokenType.IDENTIFIER):
            node = IdentifierExpr(name=tok.lexeme, line=tok.line)
        elif self._match(TokenType.LPAREN):
            node = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
        else:
            sys.exit(print(f"[ERRO SINTATICO] Linha {tok.line}: Expressao esperada", file=sys.stderr) or 1)

        # Loop de encadeamento (Ponto, Indexação, Chamadas)
        while True:
            if self._match(TokenType.DOT):
                prop_tok = self._consume(TokenType.IDENTIFIER, "Esperado identificador apos '.'")
                if self._match(TokenType.LPAREN):
                    args = []
                    if self._peek().type != TokenType.RPAREN:
                        args.append(self._parse_expression())
                        while self._match(TokenType.COMMA): args.append(self._parse_expression())
                    self._consume(TokenType.RPAREN, "Esperado ')'")
                    node = MethodCall(object=node, method_name=prop_tok.lexeme, arguments=args, line=prop_tok.line)
                else:
                    node = PropertyAccess(object=node, property_name=prop_tok.lexeme, line=prop_tok.line)
            elif self._match(TokenType.LBRACKET):
                idx_tok = self._tokens[self._pos - 1]
                idx = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Esperado ']'")
                node = IndexExpr(object=node, index=idx, line=idx_tok.line)
            else:
                break

        return node

    def parse(self) -> Program:
        prog = Program()
        while self._peek().type != TokenType.END_OF_FILE:
            stmt = self._parse_statement()
            if stmt: prog.statements.append(stmt)
        return prog