from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional
from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt, IdentifierExpr, BinaryExpr, 
    UnaryExpr, SeqBlock, ParBlock, IfStmt, WhileStmt,
    ClassDecl, FuncDecl, ReturnStmt, MethodCall, FuncCallExpr, PropertyAccess, PropertyAssign, NewExpr, ThisExpr,
    CChannelExpr, SendStmt, ReceiveExpr, ListLiteral, MatrixCreateExpr, IndexExpr, IndexAssign
)

@dataclass
class Symbol:
    name: str
    type: str

class SemanticAnalyzer:
    def __init__(self) -> None:
        self._scopes: List[Dict[str, Symbol]] = []
        self._has_errors = False
        self._current_function: Optional[str] = None
        self._enter_scope()

    def _enter_scope(self) -> None: self._scopes.append({})
    def _exit_scope(self) -> None:
        if len(self._scopes) > 1: self._scopes.pop()

    def _get_context(self) -> str:
        return f" (Funcao: {self._current_function})" if self._current_function else ""

    def _define_symbol(self, name: str, type_: str, line: int) -> None:
        if name in self._scopes[-1]:
            print(f"[ERRO SEMANTICO] Linha {line}{self._get_context()}: Variavel '{name}' ja declarada.", file=sys.stderr)
            self._has_errors = True
        else: self._scopes[-1][name] = Symbol(name=name, type=type_)

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self._scopes):
            if name in scope: return scope[name]
        return None

    def validate_node(self, node: ASTNode) -> None:
        if node is None: return

        if isinstance(node, VarDecl):
            self._define_symbol(node.name, "VAR", node.line)
            self.validate_node(node.init_value)
        elif isinstance(node, Assignment):
            if self._lookup(node.name) is None:
                print(f"[ERRO SEMANTICO] Linha {node.line}{self._get_context()}: Variavel '{node.name}' nao declarada.", file=sys.stderr)
                self._has_errors = True
            self.validate_node(node.value)
        elif isinstance(node, PrintStmt):
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, SendStmt):
            self.validate_node(node.channel)
            self.validate_node(node.message)
        elif isinstance(node, CChannelExpr):
            self.validate_node(node.ip)
            self.validate_node(node.port)
        elif isinstance(node, ReceiveExpr):
            self.validate_node(node.channel)
        elif isinstance(node, ListLiteral):
            for e in node.elements: self.validate_node(e)
        elif isinstance(node, MatrixCreateExpr):
            self.validate_node(node.rows)
            self.validate_node(node.cols)
            self.validate_node(node.init_value)
        elif isinstance(node, IndexExpr):
            self.validate_node(node.object)
            self.validate_node(node.index)
        elif isinstance(node, IndexAssign):
            self.validate_node(node.target)
            self.validate_node(node.value)
        elif isinstance(node, IdentifierExpr):
            if self._lookup(node.name) is None:
                pass
        elif isinstance(node, BinaryExpr):
            self.validate_node(node.left)
            self.validate_node(node.right)
        elif isinstance(node, UnaryExpr):
            self.validate_node(node.operand)
        elif isinstance(node, (SeqBlock, ParBlock)):
            self._enter_scope()
            for stmt in node.statements: self.validate_node(stmt)
            self._exit_scope()
        elif isinstance(node, IfStmt):
            self.validate_node(node.condition)
            self.validate_node(node.then_branch)
            if node.else_branch: self.validate_node(node.else_branch)
        elif isinstance(node, WhileStmt):
            self.validate_node(node.condition)
            self.validate_node(node.body)
        elif isinstance(node, ClassDecl):
            self._define_symbol(node.name, "CLASS", node.line)
            self._enter_scope()
            for attr in node.attributes: self.validate_node(attr)
            for method in node.methods: self.validate_node(method)
            self._exit_scope()
        elif isinstance(node, FuncDecl):
            self._define_symbol(node.name, "FUNC", node.line)
            self._enter_scope()
            old_function = self._current_function
            self._current_function = node.name
            for p in node.params: self._define_symbol(p, "PARAM", node.line)
            self.validate_node(node.body)
            self._current_function = old_function
            self._exit_scope()
        elif isinstance(node, ReturnStmt):
            if node.value: self.validate_node(node.value)
        elif isinstance(node, MethodCall):
            self.validate_node(node.object)
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, FuncCallExpr):
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, PropertyAccess):
            self.validate_node(node.object)
        elif isinstance(node, PropertyAssign):
            self.validate_node(node.object)
            self.validate_node(node.value)
        elif isinstance(node, NewExpr):
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, ThisExpr):
            pass

    def analyze(self, program: Program) -> bool:
        for stmt in program.statements: self.validate_node(stmt)
        return not self._has_errors