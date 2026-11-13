"""Safe Formula and Calculated Column Engine for DataLens.

Provides AST-based tokenization, parsing, validation, and SQL generation
without executing arbitrary code or using eval/exec.
"""
from __future__ import annotations

import re
from typing import Any


class FormulaError(Exception):
    """Raised when a formula cannot be parsed or validated."""
    pass


class Token:
    def __init__(self, type_: str, value: Any, pos: int):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, pos={self.pos})"


class FormulaTokenizer:
    """Tokenizes formula expressions supporting BI column syntax [Col Name]."""

    TOKEN_SPEC = [
        ("SKIP", r"[ \t\r\n]+"),
        ("NUMBER", r"\d+(\.\d*)?([eE][+-]?\d+)?"),
        ("STRING_SQ", r"'([^'\\]*(?:\\.[^'\\]*)*)'"),
        ("STRING_DQ", r'"([^"\\]*(?:\\.[^"\\]*)*)"'),
        ("BRACKET_COL", r"\[([^\]]+)\]"),
        ("OP_EQ", r"=="),
        ("OP_NEQ", r"!="),
        ("OP_NEQ2", r"<>"),
        ("OP_LTE", r"<="),
        ("OP_GTE", r">="),
        ("OP_LT", r"<"),
        ("OP_GT", r">"),
        ("OP_ASSIGN", r"="),
        ("OP_PLUS", r"\+"),
        ("OP_MINUS", r"-"),
        ("OP_MULT", r"\*"),
        ("OP_DIV", r"/"),
        ("OP_MOD", r"%"),
        ("OP_POW", r"\^"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("COMMA", r","),
        ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ]

    MASTER_REGEX = re.compile("|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in TOKEN_SPEC))

    @classmethod
    def tokenize(cls, text: str) -> list[Token]:
        tokens: list[Token] = []
        for match in cls.MASTER_REGEX.finditer(text):
            kind = match.lastgroup
            val = match.group()
            pos = match.start()
            if kind == "SKIP":
                continue
            elif kind == "NUMBER":
                num_val = float(val) if ("." in val or "e" in val or "E" in val) else int(val)
                tokens.append(Token("NUMBER", num_val, pos))
            elif kind == "STRING_SQ":
                unquoted = val[1:-1].replace("\\'", "'").replace('\\"', '"')
                tokens.append(Token("STRING", unquoted, pos))
            elif kind == "STRING_DQ":
                unquoted = val[1:-1].replace('\\"', '"').replace("\\'", "'")
                tokens.append(Token("STRING", unquoted, pos))
            elif kind == "BRACKET_COL":
                col_name = val[1:-1].strip()
                tokens.append(Token("COLUMN", col_name, pos))
            elif kind == "IDENT":
                upper_val = val.upper()
                if upper_val == "AND":
                    tokens.append(Token("OP_AND", "AND", pos))
                elif upper_val == "OR":
                    tokens.append(Token("OP_OR", "OR", pos))
                elif upper_val == "NOT":
                    tokens.append(Token("OP_NOT", "NOT", pos))
                elif upper_val == "TRUE":
                    tokens.append(Token("BOOLEAN", True, pos))
                elif upper_val == "FALSE":
                    tokens.append(Token("BOOLEAN", False, pos))
                elif upper_val == "NULL":
                    tokens.append(Token("NULL", None, pos))
                else:
                    tokens.append(Token("IDENT", val, pos))
            elif kind in ("OP_EQ", "OP_ASSIGN"):
                tokens.append(Token("OP_COMP", "=", pos))
            elif kind in ("OP_NEQ", "OP_NEQ2"):
                tokens.append(Token("OP_COMP", "!=", pos))
            elif kind in ("OP_LTE", "OP_GTE", "OP_LT", "OP_GT"):
                tokens.append(Token("OP_COMP", val, pos))
            elif kind in ("OP_PLUS", "OP_MINUS"):
                tokens.append(Token("OP_ADD", val, pos))
            elif kind in ("OP_MULT", "OP_DIV", "OP_MOD"):
                tokens.append(Token("OP_MULT", val, pos))
            elif kind == "OP_POW":
                tokens.append(Token("OP_POW", "^", pos))
            elif kind in ("LPAREN", "RPAREN", "COMMA"):
                tokens.append(Token(kind, val, pos))
            else:
                raise FormulaError(f"Unexpected token {val!r} at position {pos}")
        return tokens


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

class ASTNode:
    def to_sql(self) -> str:
        raise NotImplementedError

    def get_columns(self) -> set[str]:
        return set()

    def describe(self) -> str:
        return self.__class__.__name__


class NumberNode(ASTNode):
    def __init__(self, val: int | float):
        self.val = val

    def to_sql(self) -> str:
        return str(self.val)

    def describe(self) -> str:
        return f"Number({self.val})"


class StringNode(ASTNode):
    def __init__(self, val: str):
        self.val = val

    def to_sql(self) -> str:
        escaped = self.val.replace("'", "''")
        return f"'{escaped}'"

    def describe(self) -> str:
        return f"String('{self.val}')"


class BooleanNode(ASTNode):
    def __init__(self, val: bool):
        self.val = val

    def to_sql(self) -> str:
        return "TRUE" if self.val else "FALSE"

    def describe(self) -> str:
        return f"Boolean({self.val})"


class NullNode(ASTNode):
    def to_sql(self) -> str:
        return "NULL"

    def describe(self) -> str:
        return "Null"


class ColumnNode(ASTNode):
    def __init__(self, name: str):
        self.name = name

    def to_sql(self) -> str:
        escaped = self.name.replace('"', '""')
        return f'"{escaped}"'

    def get_columns(self) -> set[str]:
        return {self.name}

    def describe(self) -> str:
        return f"Column([{self.name}])"


class UnaryOpNode(ASTNode):
    def __init__(self, op: str, operand: ASTNode):
        self.op = op
        self.operand = operand

    def to_sql(self) -> str:
        if self.op.upper() == "NOT":
            return f"(NOT {self.operand.to_sql()})"
        return f"({self.op}{self.operand.to_sql()})"

    def get_columns(self) -> set[str]:
        return self.operand.get_columns()

    def describe(self) -> str:
        return f"Unary({self.op} {self.operand.describe()})"


class BinaryOpNode(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right

    def to_sql(self) -> str:
        left_sql = self.left.to_sql()
        right_sql = self.right.to_sql()
        if self.op == "/":
            # Safe divide by zero prevention
            return f"({left_sql} / NULLIF({right_sql}, 0))"
        elif self.op == "^":
            return f"POWER({left_sql}, {right_sql})"
        return f"({left_sql} {self.op} {right_sql})"

    def get_columns(self) -> set[str]:
        return self.left.get_columns() | self.right.get_columns()

    def describe(self) -> str:
        return f"Binary({self.left.describe()} {self.op} {self.right.describe()})"


class FunctionCallNode(ASTNode):
    ALLOWED_FUNCTIONS = {
        "IF", "COALESCE", "ISNULL", "CONCAT", "UPPER", "LOWER", "TRIM",
        "LENGTH", "ROUND", "ABS", "FLOOR", "CEIL", "CEILING", "POWER", "SUBSTRING"
    }

    def __init__(self, name: str, args: list[ASTNode]):
        self.name = name.upper()
        if self.name not in self.ALLOWED_FUNCTIONS:
            raise FormulaError(f"Unsupported function '{name}'. Allowed: {', '.join(sorted(self.ALLOWED_FUNCTIONS))}")
        self.args = args

    def to_sql(self) -> str:
        arg_sqls = [arg.to_sql() for arg in self.args]
        if self.name == "IF":
            if len(self.args) != 3:
                raise FormulaError("IF() requires exactly 3 arguments: IF(condition, then_value, else_value)")
            return f"(CASE WHEN {arg_sqls[0]} THEN {arg_sqls[1]} ELSE {arg_sqls[2]} END)"
        elif self.name in ("COALESCE", "ISNULL"):
            if not self.args:
                raise FormulaError(f"{self.name}() requires at least 1 argument")
            return f"COALESCE({', '.join(arg_sqls)})"
        elif self.name == "CONCAT":
            return f"CONCAT({', '.join(arg_sqls)})"
        elif self.name in ("UPPER", "LOWER", "TRIM", "LENGTH", "ABS", "FLOOR", "CEIL", "CEILING"):
            if len(self.args) != 1:
                raise FormulaError(f"{self.name}() requires exactly 1 argument")
            fn = "CEIL" if self.name == "CEILING" else self.name
            return f"{fn}({arg_sqls[0]})"
        elif self.name == "ROUND":
            if len(self.args) == 1:
                return f"ROUND({arg_sqls[0]}, 0)"
            elif len(self.args) == 2:
                return f"ROUND({arg_sqls[0]}, {arg_sqls[1]})"
            else:
                raise FormulaError("ROUND() takes 1 or 2 arguments: ROUND(val, [decimals])")
        elif self.name == "POWER":
            if len(self.args) != 2:
                raise FormulaError("POWER() requires 2 arguments: POWER(base, exponent)")
            return f"POWER({arg_sqls[0]}, {arg_sqls[1]})"
        elif self.name == "SUBSTRING":
            if len(self.args) not in (2, 3):
                raise FormulaError("SUBSTRING() requires 2 or 3 arguments: SUBSTRING(str, start, [length])")
            return f"SUBSTRING({', '.join(arg_sqls)})"
        return f"{self.name}({', '.join(arg_sqls)})"

    def get_columns(self) -> set[str]:
        cols: set[str] = set()
        for arg in self.args:
            cols |= arg.get_columns()
        return cols

    def describe(self) -> str:
        args_desc = ", ".join(arg.describe() for arg in self.args)
        return f"Func({self.name}, [{args_desc}])"


# ---------------------------------------------------------------------------
# Recursive Descent Parser
# ---------------------------------------------------------------------------

class FormulaParser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self) -> Token:
        tok = self.current_token()
        self.pos += 1
        return tok  # type: ignore

    def expect(self, tok_type: str) -> Token:
        tok = self.current_token()
        if not tok or tok.type != tok_type:
            got = tok.type if tok else "EOF"
            raise FormulaError(f"Expected {tok_type}, found {got} at token position {self.pos}")
        return self.advance()

    def parse(self) -> ASTNode:
        if not self.tokens:
            raise FormulaError("Formula is empty")
        node = self.parse_or()
        if self.current_token() is not None:
            tok = self.current_token()
            raise FormulaError(f"Unexpected trailing token '{tok.value}' at pos {tok.pos}")  # type: ignore
        return node

    def parse_or(self) -> ASTNode:
        left = self.parse_and()
        while self.current_token() and self.current_token().type == "OP_OR":  # type: ignore
            self.advance()
            right = self.parse_and()
            left = BinaryOpNode(left, "OR", right)
        return left

    def parse_and(self) -> ASTNode:
        left = self.parse_not()
        while self.current_token() and self.current_token().type == "OP_AND":  # type: ignore
            self.advance()
            right = self.parse_not()
            left = BinaryOpNode(left, "AND", right)
        return left

    def parse_not(self) -> ASTNode:
        if self.current_token() and self.current_token().type == "OP_NOT":  # type: ignore
            self.advance()
            operand = self.parse_comp()
            return UnaryOpNode("NOT", operand)
        return self.parse_comp()

    def parse_comp(self) -> ASTNode:
        left = self.parse_add()
        while self.current_token() and self.current_token().type == "OP_COMP":  # type: ignore
            op_tok = self.advance()
            right = self.parse_add()
            left = BinaryOpNode(left, op_tok.value, right)
        return left

    def parse_add(self) -> ASTNode:
        left = self.parse_mult()
        while self.current_token() and self.current_token().type == "OP_ADD":  # type: ignore
            op_tok = self.advance()
            right = self.parse_mult()
            left = BinaryOpNode(left, op_tok.value, right)
        return left

    def parse_mult(self) -> ASTNode:
        left = self.parse_unary()
        while self.current_token() and self.current_token().type == "OP_MULT":  # type: ignore
            op_tok = self.advance()
            right = self.parse_unary()
            left = BinaryOpNode(left, op_tok.value, right)
        return left

    def parse_unary(self) -> ASTNode:
        if self.current_token() and self.current_token().type == "OP_ADD":  # type: ignore
            op_tok = self.advance()
            operand = self.parse_power()
            return UnaryOpNode(op_tok.value, operand)
        return self.parse_power()

    def parse_power(self) -> ASTNode:
        left = self.parse_primary()
        if self.current_token() and self.current_token().type == "OP_POW":  # type: ignore
            self.advance()
            right = self.parse_power()
            return BinaryOpNode(left, "^", right)
        return left

    def parse_primary(self) -> ASTNode:
        tok = self.current_token()
        if not tok:
            raise FormulaError("Unexpected end of formula")

        if tok.type == "NUMBER":
            self.advance()
            return NumberNode(tok.value)
        elif tok.type == "STRING":
            self.advance()
            return StringNode(tok.value)
        elif tok.type == "BOOLEAN":
            self.advance()
            return BooleanNode(tok.value)
        elif tok.type == "NULL":
            self.advance()
            return NullNode()
        elif tok.type == "COLUMN":
            self.advance()
            return ColumnNode(tok.value)
        elif tok.type == "LPAREN":
            self.advance()
            expr = self.parse_or()
            self.expect("RPAREN")
            return expr
        elif tok.type == "IDENT":
            ident_name = tok.value
            self.advance()
            # If followed by '(', it is a function call
            if self.current_token() and self.current_token().type == "LPAREN":  # type: ignore
                self.advance()
                args: list[ASTNode] = []
                if self.current_token() and self.current_token().type != "RPAREN":  # type: ignore
                    args.append(self.parse_or())
                    while self.current_token() and self.current_token().type == "COMMA":  # type: ignore
                        self.advance()
                        args.append(self.parse_or())
                self.expect("RPAREN")
                return FunctionCallNode(ident_name, args)
            else:
                # Bare identifier is treated as a column reference
                return ColumnNode(ident_name)
        else:
            raise FormulaError(f"Unexpected token '{tok.value}' (type {tok.type}) at pos {tok.pos}")


# ---------------------------------------------------------------------------
# Formula Engine Public Interface
# ---------------------------------------------------------------------------

class FormulaEngine:
    """Validates formulas, checks column dependencies, and produces safe SQL."""

    @classmethod
    def parse_and_validate(
        cls,
        expression: str,
        available_columns: list[str] | set[str] | None = None,
    ) -> tuple[ASTNode, str, list[str]]:
        """Parses an expression and validates that referenced columns exist.

        Returns (ast_node, sql_expression, referenced_columns).
        """
        trimmed = expression.strip()
        if not trimmed:
            raise FormulaError("Formula cannot be empty")

        tokens = FormulaTokenizer.tokenize(trimmed)
        parser = FormulaParser(tokens)
        ast = parser.parse()

        referenced_cols = sorted(list(ast.get_columns()))

        if available_columns is not None:
            avail_set = set(available_columns)
            missing = [c for c in referenced_cols if c not in avail_set]
            if missing:
                raise FormulaError(f"Unknown column(s) in formula: {', '.join(missing)}")

        sql_expr = ast.to_sql()
        return ast, sql_expr, referenced_cols
