from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt,
    IdentifierExpr, BinaryExpr, UnaryExpr, SeqBlock, ParBlock,
    IfStmt, WhileStmt
)


@dataclass
class Symbol:
    name: str
    type: str


class SemanticAnalyzer:
    def __init__(self) -> None:
        self._scopes: List[Dict[str, Symbol]] = []
        self._has_errors = False
        self._enter_scope()  # Escopo global

    # ------------------------------------------------------------------ #
    # Gerenciamento de escopos                                             #
    # ------------------------------------------------------------------ #

    def _enter_scope(self) -> None:
        self._scopes.append({})

    def _exit_scope(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()

    def _define_symbol(self, name: str, type_: str, line: int) -> None:
        if name in self._scopes[-1]:
            print(
                f"[ERRO SEMANTICO] Linha {line}: Variavel '{name}' ja declarada neste escopo.",
                file=sys.stderr,
            )
            self._has_errors = True
        else:
            self._scopes[-1][name] = Symbol(name=name, type=type_)

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    # ------------------------------------------------------------------ #
    # Validação de nós                                                     #
    # ------------------------------------------------------------------ #

    def validate_node(self, node: ASTNode) -> None:
        if node is None:
            return

        if isinstance(node, VarDecl):
            self._define_symbol(node.name, "VAR", node.line)
            self.validate_node(node.init_value)

        elif isinstance(node, Assignment):
            if self._lookup(node.name) is None:
                print(
                    f"[ERRO SEMANTICO] Linha {node.line}: Variavel '{node.name}' nao declarada.",
                    file=sys.stderr,
                )
                self._has_errors = True
            self.validate_node(node.value)

        elif isinstance(node, PrintStmt):
            for arg in node.arguments:
                self.validate_node(arg)

        elif isinstance(node, IdentifierExpr):
            if self._lookup(node.name) is None:
                print(
                    f"[ERRO SEMANTICO] Linha {node.line}: Variavel '{node.name}' nao declarada.",
                    file=sys.stderr,
                )
                self._has_errors = True

        elif isinstance(node, BinaryExpr):
            self.validate_node(node.left)
            self.validate_node(node.right)

        elif isinstance(node, UnaryExpr):
            self.validate_node(node.operand)

        elif isinstance(node, SeqBlock):
            self._enter_scope()
            for stmt in node.statements:
                self.validate_node(stmt)
            self._exit_scope()

        elif isinstance(node, ParBlock):
            self._enter_scope()
            for stmt in node.statements:
                self.validate_node(stmt)
            self._exit_scope()

        elif isinstance(node, IfStmt):
            self.validate_node(node.condition)
            self.validate_node(node.then_branch)
            if node.else_branch:
                self.validate_node(node.else_branch)

        elif isinstance(node, WhileStmt):
            self.validate_node(node.condition)
            self.validate_node(node.body)

    # ------------------------------------------------------------------ #
    # Ponto de entrada                                                     #
    # ------------------------------------------------------------------ #

    def analyze(self, program: Program) -> bool:
        for stmt in program.statements:
            self.validate_node(stmt)
        return not self._has_errors