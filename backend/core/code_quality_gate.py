"""Compile-only validation and advisory lint for generated Python source.

This module never executes source, writes bytecode, imports the backend app, or
proves that a program is safe to run. Authentication, tool permissions and runtime
isolation must remain separate. By default only syntax/compilation/sanitization
failures block; ``strict=True`` also blocks the explicitly heuristic lint rules.
"""
from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class _Scope:
    kind: str
    parent: _Scope | None
    name: str
    bindings: set[str] = field(default_factory=set)
    imports: dict[str, tuple[int, bool]] = field(default_factory=dict)
    loads: list[tuple[str, int]] = field(default_factory=list)
    globals: set[str] = field(default_factory=set)
    nonlocals: set[str] = field(default_factory=set)
    used_imports: set[str] = field(default_factory=set)


def _execution_nodes(statements: list[ast.stmt]) -> Iterator[ast.AST]:
    """Walk a suite without attributing nested functions/classes to its runtime."""
    pending: list[ast.AST] = list(reversed(statements))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


def _broad_exception(node: ast.expr | None) -> bool:
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in {"Exception", "BaseException"}
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id == "builtins" and node.attr in {"Exception", "BaseException"}
    return isinstance(node, ast.Tuple) and any(_broad_exception(part) for part in node.elts)


class LLMCodeQualityGate(ast.NodeVisitor):
    """Detect review hints, with scoped import use and optional strict lint.

    ``errors`` and ``finalize()`` retain the original interface. Findings are
    advisory in ``warnings`` by default because sequential I/O, broad exception
    generators and apparently unused imports can all be deliberate. This is a
    conservative source analysis, not a complete Python name resolver or a
    security policy. Dynamic import use may still need human review.
    """

    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.diagnostics: list[dict[str, Any]] = []
        self.imported_names: dict[str, int] = {}
        self.used_names: set[str] = set()
        self._root = _Scope("module", None, "module")
        self._scope = self._root
        self._scopes = [self._root]
        self._reported: set[tuple[str, int, str]] = set()
        self._exports: set[str] = set()
        self._dynamic_exports = False

    def _hint(self, code: str, node: ast.AST, message: str) -> None:
        line = getattr(node, "lineno", 0)
        key = (code, line, message)
        if key in self._reported:
            return
        self._reported.add(key)
        description = f"Line {line}: {code}: {message}"
        self.warnings.append(description)
        if self.strict:
            self.errors.append(description)
        self.diagnostics.append({
            "severity": "error" if self.strict else "warning",
            "code": code, "line": line,
            "column": getattr(node, "col_offset", 0) + 1,
            "message": message,
        })

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            reexport = self._scope.kind == "module" and alias.asname == alias.name
            self._scope.bindings.add(name)
            self._scope.imports[name] = (node.lineno, reexport)
            self.imported_names[name] = node.lineno

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "__future__":
            return
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            reexport = self._scope.kind == "module" and alias.asname == alias.name
            self._scope.bindings.add(name)
            self._scope.imports[name] = (node.lineno, reexport)
            self.imported_names[name] = node.lineno

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._scope.loads.append((node.id, node.lineno))
            self.used_names.add(node.id)
        else:
            self._scope.bindings.add(node.id)

    def visit_Global(self, node: ast.Global) -> None:
        self._scope.globals.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._scope.nonlocals.update(node.names)

    def _annotation(self, node: ast.expr | None) -> None:
        if node is None:
            return
        self.visit(node)
        # Quoted forward annotations may be the only use of a type import.
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                expression = ast.parse(node.value, mode="eval")
            except (SyntaxError, ValueError, RecursionError):
                return
            for part in ast.walk(expression):
                if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Load):
                    self._scope.loads.append((part.id, node.lineno))
                    self.used_names.add(part.id)

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> None:
        if not isinstance(node, ast.Lambda):
            self._scope.bindings.add(node.name)
            for decorator in node.decorator_list:
                self.visit(decorator)
            self._annotation(node.returns)
            for parameter in getattr(node, "type_params", []):
                self.visit(parameter)
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                self.visit(default)
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        arguments += [a for a in (node.args.vararg, node.args.kwarg) if a is not None]
        for argument in arguments:
            self._annotation(argument.annotation)
        parent = self._scope
        child = _Scope("function", parent, getattr(node, "name", "lambda"))
        child.bindings.update(argument.arg for argument in arguments)
        self._scopes.append(child)
        self._scope = child
        if isinstance(node, ast.Lambda):
            self.visit(node.body)
        else:
            for statement in node.body:
                self.visit(statement)
        self._scope = parent

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function
    visit_Lambda = _function

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.bindings.add(node.name)
        for expression in [*node.decorator_list, *node.bases, *node.keywords, *getattr(node, "type_params", [])]:
            self.visit(expression)
        parent = self._scope
        self._scope = _Scope("class", parent, node.name)
        self._scopes.append(self._scope)
        for statement in node.body:
            self.visit(statement)
        self._scope = parent

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._annotation(node.annotation)
        self.visit(node.target)
        if node.value is not None:
            self.visit(node.value)

    def _exports_assignment(self, targets: list[ast.expr], value: ast.expr | None) -> None:
        if self._scope.kind != "module" or not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            return
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts):
            self._exports.update(e.value for e in value.elts)
        else:
            self._dynamic_exports = True

    def visit_Assign(self, node: ast.Assign) -> None:
        self._exports_assignment(node.targets, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._exports_assignment([node.target], node.value)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try | ast.TryStar) -> None:
        if any(_broad_exception(handler.type) for handler in node.handlers):
            for child in _execution_nodes(node.body):
                if isinstance(child, (ast.Yield, ast.YieldFrom)):
                    self._hint("BROAD_EXCEPT_YIELD", child,
                        "A generator yields inside a broad exception handler's protected suite. Review exception propagation; this can be intentional.")
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_For(self, node: ast.For | ast.AsyncFor) -> None:
        for child in _execution_nodes(node.body):
            if isinstance(child, ast.Await):
                self._hint("SEQUENTIAL_AWAIT", child,
                    "The loop awaits each iteration. Review ordering and rate limits before considering bounded concurrency.")
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def _resolve_import_use(self, scope: _Scope, name: str) -> None:
        if name in scope.globals:
            if name in self._root.imports:
                self._root.used_imports.add(name)
            return
        current: _Scope | None = scope
        if name in scope.nonlocals:
            current = scope.parent
        while current is not None:
            if current is scope or current.kind != "class":
                if name in current.bindings:
                    if name in current.imports:
                        current.used_imports.add(name)
                    return
            current = current.parent

    def finalize(self) -> list[str]:
        """Return blocking findings; repeat calls do not duplicate diagnostics."""
        for scope in self._scopes:
            for name, _ in scope.loads:
                self._resolve_import_use(scope, name)
        for scope in self._scopes:
            for name, (line, reexport) in scope.imports.items():
                exported = scope is self._root and (self._dynamic_exports or name in self._exports)
                if name not in scope.used_imports and not reexport and not exported:
                    node = ast.Name(id=name, ctx=ast.Load(), lineno=line, col_offset=0)
                    self._hint("UNUSED_IMPORT", node,
                        f"Import '{name}' in scope '{scope.name}' has no statically resolved reference. It may be used dynamically or for registration side effects.")
        return self.errors


def _sanitize_source(source: str) -> tuple[str, list[dict[str, Any]]]:
    """Normalize invisible padding only where token boundaries are unambiguous."""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def position(point: tuple[int, int]) -> int:
        row, column = point
        return offsets[min(row - 1, len(offsets) - 1)] + column

    protected: list[tuple[int, int]] = []
    fstring_starts: list[int] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.STRING, tokenize.COMMENT):
            protected.append((position(token.start), position(token.end)))
        elif token.type == getattr(tokenize, "FSTRING_START", -1):
            fstring_starts.append(position(token.start))
        elif token.type == getattr(tokenize, "FSTRING_END", -1):
            if not fstring_starts:
                raise ValueError("Unbalanced f-string token boundaries")
            protected.append((fstring_starts.pop(), position(token.end)))
        elif token.type == tokenize.ERRORTOKEN and token.string in {"'", '"'}:
            raise ValueError("Unterminated or ambiguous quoted source; no normalization applied")
    if fstring_starts:
        raise ValueError("Unterminated f-string; no normalization applied")
    protected.sort()
    # Merge nested f-strings with their outer literal before walking characters.
    merged: list[tuple[int, int]] = []
    for start, end in protected:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    changes: list[dict[str, Any]] = []
    fragments: list[str] = []
    range_index = 0
    line, column = 1, 1
    leading_invisible_padding = True
    for index, character in enumerate(source):
        while range_index < len(merged) and index >= merged[range_index][1]:
            range_index += 1
        literal = range_index < len(merged) and merged[range_index][0] <= index < merged[range_index][1]
        replacement = character
        if not literal and character == "\u00a0":
            replacement = " "
        elif not literal and character in {"\u200b", "\ufeff"}:
            left = source[index - 1] if index else " "
            right = source[index + 1] if index + 1 < len(source) else " "
            if not (left.isspace() or right.isspace() or index == 0):
                # Adjacent leading zero-width padding is still safe to remove.
                if not leading_invisible_padding:
                    raise ValueError(f"Ambiguous invisible character U+{ord(character):04X} at line {line}, column {column}; refusing to join tokens")
            replacement = ""
        if replacement != character:
            changes.append({"line": line, "column": column,
                "character": f"U+{ord(character):04X}", "replacement": replacement})
        fragments.append(replacement)
        if character not in "\u200b\ufeff":
            leading_invisible_padding = False
        if character == "\n":
            line, column = line + 1, 1
        else:
            column += 1
    return "".join(fragments), changes


def sanitize_and_validate_llm_code(raw_code: str, *, strict: bool = False) -> dict[str, Any]:
    """Validate without running source; ``strict=True`` also blocks lint hints.

    ``sanitized_code`` must be the exact source later executed by an authorized
    caller. The gate does not authorize execution and does not validate imports,
    dependencies, resource bounds, file access, secrets or external side effects.
    Unsupported/ambiguous text is returned unchanged with a blocking diagnostic.
    """
    clean_code = raw_code if isinstance(raw_code, str) else ""
    result: dict[str, Any] = {"valid": False, "sanitized_code": clean_code,
        "errors": [], "warnings": [], "diagnostics": [], "sanitizations": [],
        "strict": strict if isinstance(strict, bool) else False}

    def error(code: str, message: str, line: int | None = None, column: int | None = None) -> None:
        result["errors"].append(message)
        result["diagnostics"].append({"severity": "error", "code": code,
            "message": message, "line": line, "column": column})

    if not isinstance(raw_code, str) or not isinstance(strict, bool):
        error("INVALID_INPUT", "raw_code must be text and strict must be a boolean")
        return result
    try:
        raw_code.encode("utf-8", errors="strict")
        clean_code, changes = _sanitize_source(raw_code)
    except (UnicodeError, ValueError, SyntaxError, tokenize.TokenError, RecursionError) as exc:
        error("SOURCE_NORMALIZATION", f"{type(exc).__name__}: {exc}")
        return result
    result["sanitized_code"], result["sanitizations"] = clean_code, changes
    try:
        tree = ast.parse(clean_code, filename="<llm-generated>", mode="exec")
    except (SyntaxError, ValueError, RecursionError) as exc:
        error("SYNTAX_ERROR", f"{type(exc).__name__}: {exc}", getattr(exc, "lineno", None), getattr(exc, "offset", None))
        return result
    # Parsing alone permits constructs such as top-level await/return that exec
    # compilation rejects. Discard the code object: no eval/exec or .pyc writes.
    try:
        compile(tree, "<llm-generated>", "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError, RecursionError) as exc:
        error("COMPILE_ERROR", f"{type(exc).__name__}: {exc}", getattr(exc, "lineno", None), getattr(exc, "offset", None))
    try:
        gate = LLMCodeQualityGate(strict=strict)
        gate.visit(tree)
        result["errors"].extend(gate.finalize())
        result["warnings"].extend(gate.warnings)
        result["diagnostics"].extend(gate.diagnostics)
    except (ValueError, TypeError, RecursionError) as exc:
        error("ANALYSIS_ERROR", f"{type(exc).__name__}: {exc}")
    result["valid"] = not result["errors"]
    return result
