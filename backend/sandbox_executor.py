# File: c:/AI-BS/sandbox_executor.py
import argparse
import ast
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple


FORBIDDEN_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("TODO_COMMENT", re.compile(r"(?:#|//)\s*TODO\b")),
    ("ELLIPSIS_STATEMENT", re.compile(r"^\s*\.\.\.\s*$", re.MULTILINE)),
    ("PASS_STATEMENT", re.compile(r"^\s*pass(?:\s+#.*)?$", re.MULTILINE)),
)

FENCED_BLOCK_RE: re.Pattern[str] = re.compile(
    r"```([a-zA-Z0-9_+-]*)\r?\n(.*?)```", re.DOTALL
)
FILE_HEADER_RE: re.Pattern[str] = re.compile(
    r"^\s*(?:#|//)\s*File:\s*(.+?)\s*$", re.MULTILINE
)


@dataclass(frozen=True)
class CodeArtifact:
    language: str
    target_path: Optional[Path]
    content: str
    block_index: int


def extract_artifacts(raw_payload: str) -> List[CodeArtifact]:
    artifacts: List[CodeArtifact] = []
    matches: List[Tuple[str, str]] = FENCED_BLOCK_RE.findall(raw_payload)
    if not matches:
        header_match: Optional[re.Match[str]] = FILE_HEADER_RE.search(raw_payload)
        target: Optional[Path] = (
            Path(header_match.group(1).strip()) if header_match is not None else None
        )
        artifacts.append(
            CodeArtifact(
                language="python",
                target_path=target,
                content=raw_payload,
                block_index=0,
            )
        )
        return artifacts

    for idx, (lang, body) in enumerate(matches):
        normalized_lang: str = lang.strip().lower() or "python"
        header_match = FILE_HEADER_RE.search(body)
        target_path: Optional[Path] = (
            Path(header_match.group(1).strip()) if header_match is not None else None
        )
        artifacts.append(
            CodeArtifact(
                language=normalized_lang,
                target_path=target_path,
                content=body,
                block_index=idx,
            )
        )
    return artifacts


def validate_no_placeholders(artifact: CodeArtifact) -> List[str]:
    violations: List[str] = []
    if artifact.language == "diff":
        added_lines: List[str] = [
            line[1:]
            for line in artifact.content.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        inspect_text: str = "\n".join(added_lines)
    else:
        inspect_text = artifact.content

    for label, pattern in FORBIDDEN_PATTERNS:
        match: Optional[re.Match[str]] = pattern.search(inspect_text)
        if match is not None:
            violations.append(
                f"Block #{artifact.block_index} ({artifact.target_path or artifact.language}): "
                f"Forbidden placeholder pattern [{label}] matched '{match.group(0).strip()}'"
            )
    return violations


def validate_python_ast(artifact: CodeArtifact) -> List[str]:
    if artifact.language not in ("python", "py"):
        return []
    errors: List[str] = []
    filename: str = (
        str(artifact.target_path)
        if artifact.target_path is not None
        else f"<block_{artifact.block_index}>"
    )
    try:
        tree: ast.Module = ast.parse(artifact.content, filename=filename)
        compile(tree, filename=filename, mode="exec")
    except SyntaxError as exc:
        errors.append(
            f"Block #{artifact.block_index} ({filename}): SyntaxError at line {exc.lineno}, "
            f"offset {exc.offset}: {exc.msg}"
        )
        return errors

    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            errors.append(
                f"Block #{artifact.block_index} ({filename}): AST Pass node prohibited at line {node.lineno}"
            )
        elif isinstance(node, ast.Constant) and node.value is Ellipsis:
            errors.append(
                f"Block #{artifact.block_index} ({filename}): AST Ellipsis constant prohibited at line {node.lineno}"
            )
    return errors


def atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: str = ""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(target.parent),
        prefix=f"{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = handle.name
    os.replace(temp_path, target)


def execute_standalone_python(artifact: CodeArtifact) -> Tuple[int, str, str]:
    if '__name__ == "__main__"' not in artifact.content and "__name__ == '__main__'" not in artifact.content:
        return 0, "", ""
    temp_script: str = ""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix="_codex_sandbox.py",
        delete=False,
    ) as handle:
        handle.write(artifact.content)
        handle.flush()
        temp_script = handle.name
    try:
        proc: subprocess.CompletedProcess[str] = subprocess.run(
            [sys.executable, temp_script],
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=30,
            check=False,
        )
        return int(proc.returncode), proc.stdout, proc.stderr
    finally:
        Path(temp_script).unlink(missing_ok=True)


def run_strict_ingest(raw_payload: str, apply_files: bool) -> Tuple[int, Dict[str, int]]:
    artifacts: List[CodeArtifact] = extract_artifacts(raw_payload)
    all_errors: List[str] = []
    written_count: int = 0

    for artifact in artifacts:
        all_errors.extend(validate_no_placeholders(artifact))
        all_errors.extend(validate_python_ast(artifact))

    if all_errors:
        for err in all_errors:
            sys.stderr.write(f"[STRICT-INGEST REJECTED] {err}\n")
        return 2, {"blocks": len(artifacts), "written": 0, "errors": len(all_errors)}

    if apply_files:
        for artifact in artifacts:
            if artifact.target_path is not None and artifact.language != "diff":
                atomic_write(artifact.target_path, artifact.content)
                written_count += 1

    sys.stdout.write(
        f"STRICT-INGEST VERIFIED: {len(artifacts)} block(s) validated, {written_count} file(s) committed.\n"
    )

    if len(artifacts) == 1 and artifacts[0].language in ("python", "py"):
        rc, out, err = execute_standalone_python(artifacts[0])
        if out:
            sys.stdout.write(out)
            if not out.endswith("\n"):
                sys.stdout.write("\n")
        if rc != 0:
            sys.stderr.write(f"[SANDBOX EXECUTION ERROR] {err}\n")
            return rc, {"blocks": 1, "written": written_count, "errors": 1}

    return 0, {"blocks": len(artifacts), "written": written_count, "errors": 0}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Codex Sandbox Strict-Ingest Executor"
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["strict-ingest", "validate-only"],
        help="Execution mode for incoming payload.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Write validated file blocks with explicit '# File:' headers to disk.",
    )
    return parser.parse_args(list(argv))


def main(argv: Optional[Sequence[str]] = None) -> int:
    args: argparse.Namespace = parse_args(argv if argv is not None else sys.argv[1:])
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    payload: str = sys.stdin.read()
    if not payload.strip():
        sys.stderr.write("[STRICT-INGEST REJECTED] Empty stdin payload.\n")
        return 1

    should_apply: bool = bool(args.apply) and args.mode == "strict-ingest"
    exit_code, _ = run_strict_ingest(payload, apply_files=should_apply)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
