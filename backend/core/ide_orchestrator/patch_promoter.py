import os
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional

# Import prerequisite modules defined previously
from implication_evaluator import ImplicationRiskEvaluator, RiskReport
from sandbox_runner import SubprocessSandboxRunner, SandboxResult

@dataclass
class PromotionResult:
    status: str  # "PROMOTED", "BLOCKED_RISK", "BLOCKED_SANDBOX", "GIT_ERROR", "FILE_WRITE_ERROR"
    target_file: str
    risk_report: Dict[str, Any]
    sandbox_result: Dict[str, Any]
    git_commit_hash: Optional[str]
    audit_log_path: str

class PatchPromoter:
    def __init__(
        self,
        workspace_root: str,
        symbol_graph_path: str,
        max_risk_threshold: int = 30,
        enable_git_commit: bool = True
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.symbol_graph_path = Path(symbol_graph_path).resolve()
        self.max_risk_threshold = max_risk_threshold
        self.enable_git_commit = enable_git_commit
        
        # Load local symbol graph
        self.symbol_graph = self._load_symbol_graph()
        
        # Initialize internal gatekeepers
        self.evaluator = ImplicationRiskEvaluator(
            symbol_graph=self.symbol_graph,
            max_threshold=self.max_risk_threshold
        )
        self.sandbox_runner = SubprocessSandboxRunner(default_timeout_sec=15.0)

    def promote_patch(
        self,
        rel_target_path: str,
        new_code_content: str,
        test_script_code: Optional[str] = None
    ) -> PromotionResult:
        full_target_path = self.workspace_root / rel_target_path
        audit_dir = self.workspace_root / ".ide_audit_logs"
        audit_dir.mkdir(exist_ok=True)
        audit_file = audit_dir / f"promotion_{Path(rel_target_path).stem}.json"

        # Read current code baseline for evaluation
        current_code = ""
        if full_target_path.exists():
            current_code = full_target_path.read_text(encoding="utf-8")

        # -------------------------------------------------------------
        # STEP 1: Implication Risk Evaluation
        # -------------------------------------------------------------
        risk_report: RiskReport = self.evaluator.evaluate_patch(
            patch_diff="",
            file_path=rel_target_path,
            new_code=new_code_content
        )

        if risk_report.is_blocked:
            res = PromotionResult(
                status="BLOCKED_RISK",
                target_file=rel_target_path,
                risk_report=asdict(risk_report),
                sandbox_result={},
                git_commit_hash=None,
                audit_log_path=str(audit_file)
            )
            self._write_audit_log(audit_file, res)
            return res

        # -------------------------------------------------------------
        # STEP 2: Subprocess Sandbox Validation
        # -------------------------------------------------------------
        sandbox_res: SandboxResult = self.sandbox_runner.execute_in_sandbox(
            original_file_path=str(full_target_path),
            modified_code=new_code_content,
            test_script_code=test_script_code
        )

        if sandbox_res.status != "PASSED":
            res = PromotionResult(
                status="BLOCKED_SANDBOX",
                target_file=rel_target_path,
                risk_report=asdict(risk_report),
                sandbox_result=asdict(sandbox_res),
                git_commit_hash=None,
                audit_log_path=str(audit_file)
            )
            self._write_audit_log(audit_file, res)
            return res

        # -------------------------------------------------------------
        # STEP 3: Host File System Write
        # -------------------------------------------------------------
        try:
            full_target_path.parent.mkdir(parents=True, exist_ok=True)
            full_target_path.write_text(new_code_content, encoding="utf-8")
        except Exception as e:
            res = PromotionResult(
                status="FILE_WRITE_ERROR",
                target_file=rel_target_path,
                risk_report=asdict(risk_report),
                sandbox_result=asdict(sandbox_res),
                git_commit_hash=None,
                audit_log_path=str(audit_file)
            )
            self._write_audit_log(audit_file, res)
            return res

        # -------------------------------------------------------------
        # STEP 4: Optional Git Working Tree Commit
        # -------------------------------------------------------------
        commit_hash = None
        if self.enable_git_commit:
            commit_hash = self._commit_to_git(rel_target_path)

        res = PromotionResult(
            status="PROMOTED",
            target_file=rel_target_path,
            risk_report=asdict(risk_report),
            sandbox_result=asdict(sandbox_res),
            git_commit_hash=commit_hash,
            audit_log_path=str(audit_file)
        )
        self._write_audit_log(audit_file, res)
        return res

    def _load_symbol_graph(self) -> Dict[str, Any]:
        if self.symbol_graph_path.exists():
            try:
                return json.loads(self.symbol_graph_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _commit_to_git(self, rel_target_path: str) -> Optional[str]:
        try:
            # Stage file
            subprocess.run(
                ["git", "add", rel_target_path],
                cwd=str(self.workspace_root),
                check=True,
                capture_output=True
            )
            # Commit with automated tag
            msg = f"auto(ide): verified patch promotion for {rel_target_path}"
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(self.workspace_root),
                check=True,
                capture_output=True
            )
            # Get latest commit hash
            rev_parse = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.workspace_root),
                check=True,
                capture_output=True,
                text=True
            )
            return rev_parse.stdout.strip()
        except subprocess.CalledProcessError:
            return None
        except FileNotFoundError:
            # git not installed or not in PATH
            return None

    def _write_audit_log(self, audit_file: Path, result: PromotionResult):
        audit_file.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
