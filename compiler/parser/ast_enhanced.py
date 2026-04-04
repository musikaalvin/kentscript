#!/usr/bin/env python3
"""
KentScript AST - Enhanced with proper type system
Combined from working version and Real v1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum, auto

class UnaryOp(Enum):
    NEGATE = auto()
    NOT = auto()
    BITWISE_NOT = auto()
    DEREF = auto()
    ADDR_OF = auto()

class BinaryOp(Enum):
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    POW = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    EQ = auto()
    NE = auto()
    AND = auto()
    OR = auto()
    BITWISE_AND = auto()
    BITWISE_OR = auto()
    BITWISE_XOR = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    RANGE = auto()
    INCLUSIVE_RANGE = auto()

@dataclass
class Type:
    """KentScript type with full type information"""
    name: str
    is_ptr: bool = False
    is_const: bool = False
    is_volatile: bool = False
    pointer_depth: int = 0

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    line: int = 0
    column: int = 0

@dataclass
class Literal(ASTNode):
    typ: str = ""
    value: Any = None

@dataclass
class Identifier(ASTNode):
    name: str = ""

@dataclass
class BinaryExpr(ASTNode):
    left: ASTNode = None
    op: BinaryOp = None
    right: ASTNode = None

@dataclass
class UnaryExpr(ASTNode):
    op: UnaryOp = None
    operand: ASTNode = None

@dataclass
class CallExpr(ASTNode):
    func: ASTNode = None
    args: List[ASTNode] = field(default_factory=list)

@dataclass
class IfExpr(ASTNode):
    condition: ASTNode = None
    then_body: 'Block' = None
    else_body: Optional['Block'] = None

@dataclass
class WhileExpr(ASTNode):
    condition: ASTNode = None
    body: 'Block' = None

@dataclass
class ForExpr(ASTNode):
    var: str = ""
    iter: ASTNode = None
    body: 'Block' = None

@dataclass
class Block(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode] = None

@dataclass
class BreakStmt(ASTNode):
    pass

@dataclass
class ContinueStmt(ASTNode):
    pass

@dataclass
class VarDecl(ASTNode):
    name: str = ""
    typ: Optional[Type] = None
    value: Optional[ASTNode] = None
    is_mut: bool = False
    is_const: bool = False

@dataclass
class FunctionParam:
    name: str
    typ: Type

@dataclass
class FunctionDecl(ASTNode):
    name: str = ""
    params: List[FunctionParam] = field(default_factory=list)
    return_type: Optional[Type] = None
    body: Block = None
    is_extern: bool = False
    is_unsafe: bool = False
    is_inline: bool = False
    is_pub: bool = False

@dataclass
class Program(ASTNode):
    items: List[ASTNode] = field(default_factory=list)
