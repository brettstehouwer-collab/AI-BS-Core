#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Import pipeline components
from symbol_graph_updater import SymbolGraphUpdater
from implication_evaluator import ImplicationRiskEvaluator
from sandbox_runner import SubprocessSandboxRunner
from patch_promoter import PatchPromoter

class MasterOrchestratorCLI:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.symbol_graph_path = self.workspace_root / "symbol_graph.json"
        
        # Initialize Core Subsystems
        self.graph_updater = SymbolGraphUpdater(
            workspace_root=str(self.workspace_root),
            graph_output_path=str(self.symbol_graph_path)
        )
        self.promoter = PatchPromoter(
            workspace_root=str(self.workspace_root),
            symbol_graph_path=str(self.symbol_graph_path),
            max_risk_threshold=30,
            enable_git_commit=True
        )

    def cmd_scan(self) -> int:
        """Fully re-indexes the workspace AST symbol graph."""
        print(f"[+] Scanning workspace ASTs at: {self.workspace_root}")
        graph = self.graph_updater.update_graph()
        print(f"[OK] Symbol graph successfully updated. Indexed {len(graph)} files.")
        return 0

    def cmd_evaluate(self, target_file: str, patch_file: str) -> int:
        """Performs static risk evaluation without executing sandbox or applying changes."""
        target_path = self.workspace_root / target_file
        patch_path = Path(patch_file).resolve()

        if not patch_path.exists():
            print(f"[!] Error: Patch file not found at '{patch_file}'", file=sys.stderr)
            return 1

        new_code = patch_path.read_text(encoding="utf-8")
        evaluator = ImplicationRiskEvaluator(
            symbol_graph=self.promoter.symbol_graph,
            max_threshold=30
        )
        
        report = evaluator.evaluate_patch(
            patch_diff="",
            file_path=target_file,
            new_code=new_code
        )

        print("\n=== IMPLICATION RISK REPORT ===")
        print(f"Target File:       {target_file}")
        print(f"Risk Score:        {report.risk_score} / 30")
        print(f"Evaluation Result: {'BLOCKED' if report.is_blocked else 'APPROVED'}")
        print(f"Impacted Modules:  {len(report.impacted_modules)}")
        
        if report.violations:
            print("\nViolations:")
            for v in report.violations:
                print(f"  - {v}")
                
        return 1 if report.is_blocked else 0

    def cmd_promote(self, target_file: str, patch_file: str, test_file: Optional[str] = None) -> int:
        """Runs end-to-end promotion pipeline: Risk Check -> Sandbox Test -> Host Write -> Git Commit -> Graph Update."""
        patch_path = Path(patch_file).resolve()
        if not patch_path.exists():
            print(f"[!] Error: Candidate code patch file not found: {patch_file}", file=sys.stderr)
            return 1

        new_code = patch_path.read_text(encoding="utf-8")
        test_script = None
        if test_file:
            test_path = Path(test_file).resolve()
            if test_path.exists():
                test_script = test_path.read_text(encoding="utf-8")

        # 1. Ensure symbol graph is available
        if not self.symbol_graph_path.exists():
            print("[*] Symbol graph missing. Running initial workspace scan...")
            self.graph_updater.update_graph()

        print(f"[*] Initiating Promotion Pipeline for: {target_file}")
        result = self.promoter.promote_patch(
            rel_target_path=target_file,
            new_code_content=new_code,
            test_script_code=test_script
        )

        print("\n=== PROMOTION PIPELINE RESULTS ===")
        print(f"Status:          {result.status}")
        print(f"Target File:     {result.target_file}")
        print(f"Risk Score:      {result.risk_report.get('risk_score', 'N/A')}")
        print(f"Sandbox Exit:    {result.sandbox_result.get('exit_code', 'N/A')}")
        print(f"Git Commit Hash: {result.git_commit_hash or 'None'}")
        print(f"Audit Log Path:  {result.audit_log_path}")

        if result.status == "PROMOTED":
            print("\n[*] Updating Symbol Graph for modified target...")
            self.graph_updater.update_graph(target_files=[target_file])
            print("[OK] Pipeline execution complete. Patch successfully promoted.")
            return 0
        else:
            print(f"\n[!] Promotion failed with status '{result.status}'. Check audit log for details.", file=sys.stderr)
            return 1

def main():
    parser = argparse.ArgumentParser(
        description="Master Orchestrator CLI for Self-Healing IDE Workflows"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Root path of the target codebase workspace (default: current directory)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: scan
    subparsers.add_parser("scan", help="Scan workspace ASTs and regenerate symbol_graph.json")

    # Command: evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Run static risk evaluation on a candidate patch")
    eval_parser.add_argument("--target", required=True, help="Relative target path in workspace")
    eval_parser.add_argument("--patch", required=True, help="Path to file containing new/modified candidate code")

    # Command: promote
    promote_parser = subparsers.add_parser("promote", help="Execute full promotion pipeline (Risk -> Sandbox -> Write -> Git)")
    promote_parser.add_argument("--target", required=True, help="Relative target path in workspace")
    promote_parser.add_argument("--patch", required=True, help="Path to candidate code file")
    promote_parser.add_argument("--test", required=False, help="Optional test script path for sandbox execution")

    args = parser.parse_args()
    cli = MasterOrchestratorCLI(workspace_root=args.workspace)

    if args.command == "scan":
        sys.exit(cli.cmd_scan())
    elif args.command == "evaluate":
        sys.exit(cli.cmd_evaluate(target_file=args.target, patch_file=args.patch))
    elif args.command == "promote":
        sys.exit(cli.cmd_promote(target_file=args.target, patch_file=args.patch, test_file=args.test))

if __name__ == "__main__":
    main()
