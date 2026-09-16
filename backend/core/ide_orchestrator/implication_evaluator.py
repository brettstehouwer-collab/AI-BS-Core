import ast
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class RiskReport:
    risk_score: int
    is_blocked: bool
    impacted_modules: List[str]
    violations: List[str]

class ImplicationRiskEvaluator:
    def __init__(self, symbol_graph: Dict[str, dict], max_threshold: int = 30):
        self.symbol_graph = symbol_graph
        self.max_threshold = max_threshold
        
        # System call blocklist for raw kernel/OS operations outside sandboxes
        self.forbidden_calls = {"eval", "exec", "os.system", "shutil.rmtree"}
        self.forbidden_imports = {"ctypes", "subprocess"}

    def evaluate_patch(self, patch_diff: str, file_path: str, new_code: str) -> RiskReport:
        risk_score = 0
        violations = []
        impacted_modules = []

        # 1. Parse AST of proposed code change
        try:
            tree = ast.parse(new_code)
        except SyntaxError as e:
            return RiskReport(
                risk_score=100,
                is_blocked=True,
                impacted_modules=[file_path],
                violations=[f"Syntax Error in candidate code: {str(e)}"]
            )

        # 2. Check Security & Privilege Boundaries
        for node in ast.walk(tree):
            # Check forbidden function calls
            if isinstance(node, ast.Call):
                func_name = self._get_func_name(node.func)
                if func_name in self.forbidden_calls:
                    risk_score += 100
                    violations.append(f"Hard Block: Forbidden system call '{func_name}' detected.")

            # Check forbidden imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.forbidden_imports:
                        risk_score += 50
                        violations.append(f"High Risk: Raw import '{alias.name}' bypassing sandbox boundaries.")

        # 3. Check Breaking API Signatures against Symbol Graph
        existing_symbols = self.symbol_graph.get(file_path, {}).get("functions", {})
        current_functions = {
            node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }

        for func_name, old_meta in existing_symbols.items():
            if func_name in current_functions:
                new_node = current_functions[func_name]
                old_args_count = old_meta.get("arg_count", 0)
                new_args_count = len(new_node.args.args)

                # Check if required positional arguments were altered without default values
                defaults_count = len(new_node.args.defaults)
                required_new_args = new_args_count - defaults_count

                if required_new_args > old_args_count:
                    risk_score += 40
                    violations.append(
                        f"Breaking Change: Function '{func_name}' added required parameters without defaults."
                    )

        # 4. Map Impact Radius in Symbol Graph
        dependents = self.symbol_graph.get(file_path, {}).get("dependents", [])
        impacted_modules.extend(dependents)
        if len(dependents) > 5:
            risk_score += 25
            violations.append(f"Wide Impact Radius: Patch affects {len(dependents)} downstream utilities.")

        is_blocked = risk_score >= self.max_threshold
        return RiskReport(
            risk_score=risk_score,
            is_blocked=is_blocked,
            impacted_modules=impacted_modules,
            violations=violations
        )

    def _get_func_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_func_name(node.value)}.{node.attr}"
        return ""
