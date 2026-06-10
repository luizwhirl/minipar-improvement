"""
ast_nodes.py — Nós da Árvore Sintática Abstrata (AST) do compilador MiniPar
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


class ASTNode:
    """Superclasse de todos os nós da AST."""
    line: int = 1


@dataclass
class NumberExpr(ASTNode):
    value: str
    line: int = 1


@dataclass
class StringExpr(ASTNode):
    value: str
    line: int = 1


@dataclass
class IdentifierExpr(ASTNode):
    name: str
    line: int = 1


@dataclass
class BinaryExpr(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    line: int = 1


@dataclass
class UnaryExpr(ASTNode):
    op: str
    operand: ASTNode
    line: int = 1


@dataclass
class VarDecl(ASTNode):
    name: str
    init_value: Optional[ASTNode] = None
    type: str = "var"
    line: int = 1


@dataclass
class Assignment(ASTNode):
    name: str
    value: ASTNode = None
    line: int = 1


@dataclass
class PrintStmt(ASTNode):
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1


@dataclass
class SeqBlock(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1


@dataclass
class ParBlock(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1


@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
