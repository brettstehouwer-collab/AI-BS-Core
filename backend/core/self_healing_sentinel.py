import ast
import py_compile
from typing import Any


class LLMCodeQualityGate(ast.NodeVisitor):
    """Deterministic AST analyzer that detects common LLM code generation defects."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.imported_names: dict[str, int] = {}
        self.used_names: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            bound_name = alias.asname or alias.name.split(".")[0]
            self.imported_names[bound_name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                bound_name = alias.asname or alias.name
                self.imported_names[bound_name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        has_broad_except = any(
            h.type is None or (isinstance(h.type, ast.Name) and h.type.id == "Exception")
            for h in node.handlers
        )
        if has_broad_except:
            for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                if isinstance(child, (ast.Yield, ast.YieldFrom)):
                    self.errors.append(
                        f"Line {child.lineno}: ANTI-PATTERN: 'yield' wrapped inside a broad "
                        "'try...except Exception' block. Isolate resource acquisition "
                        "from the 'try...finally' yield block."
                    )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        for child in node.body:
            for sub in ast.walk(child):
                if isinstance(sub, ast.Await):
                    self.errors.append(
                        f"Line {sub.lineno}: BOTTLENECK: Sequential 'await' inside 'for' loop. "
                        "Use 'asyncio.gather()' or 'asyncio.TaskGroup()' for concurrent I/O."
                    )
                    break
        self.generic_visit(node)

    def finalize(self) -> list[str]:
        for name, lineno in self.imported_names.items():
            if name not in self.used_names:
                self.errors.append(
                    f"Line {lineno}: DEAD IMPORT: '{name}' is imported but never referenced."
                )
        return self.errors


def sanitize_and_validate_llm_code(raw_code: str) -> dict[str, Any]:
    """
    1. Strips non-printable U+00A0 (non-breaking space) and zero-width characters.
    2. Parses AST to verify syntax integrity.
    3. Audits AST for LLM structural anti-patterns.
    """
    clean_code = (
        raw_code.replace("\u00a0", " ")
        .replace("\u200b", "")
        .replace("\ufeff", "")
    )

    try:
        tree = ast.parse(clean_code)
    except SyntaxError as exc:
        return {
            "valid": False,
            "sanitized_code": clean_code,
            "errors": [f"SyntaxError at line {exc.lineno}, col {exc.offset}: {exc.msg}"],
        }

    gate = LLMCodeQualityGate()
    gate.visit(tree)
    structural_errors = gate.finalize()

    return {
        "valid": len(structural_errors) == 0,
        "sanitized_code": clean_code,
        "errors": structural_errors,
    }
