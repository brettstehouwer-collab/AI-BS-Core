import ast
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

class SymbolGraphUpdater:
    def __init__(self, workspace_root: str, graph_output_path: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.graph_output_path = Path(graph_output_path).resolve()

    def update_graph(self, target_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scans workspace Python files, builds/updates symbol metadata, 
        calculates dependency links, and updates symbol_graph.json.
        """
        existing_graph = self._load_existing_graph()

        # Determine which files to scan
        if target_files:
            files_to_scan = [self.workspace_root / f for f in target_files]
        else:
            files_to_scan = list(self.workspace_root.rglob("*.py"))

        # Parse AST for target files
        for file_path in files_to_scan:
            if not file_path.exists() or not file_path.is_file():
                continue

            # Ignore virtual environments, git folders, and temp test runners
            if any(part.startswith((".", "venv", "__pycache__", "node_modules")) for part in file_path.parts):
                continue

            rel_path = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
            file_metadata = self._parse_file_ast(file_path)

            if file_metadata is not None:
                existing_graph[rel_path] = file_metadata

        # Recalculate inverse dependencies across the entire graph
        self._recalculate_dependents(existing_graph)

        # Write graph atomically to disk
        self._save_graph(existing_graph)
        return existing_graph

    def _parse_file_ast(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            # Skip invalid syntax or unreadable binary files
            return None

        functions: Dict[str, Dict[str, Any]] = {}
        classes: Dict[str, List[str]] = {}
        imports: Set[str] = set()

        for node in ast.walk(tree):
            # Extract Functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arg_names = [arg.arg for arg in node.args.args]
                defaults_count = len(node.args.defaults)
                functions[node.name] = {
                    "args": arg_names,
                    "arg_count": len(arg_names),
                    "defaults_count": defaults_count,
                    "required_args_count": len(arg_names) - defaults_count,
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                }

            # Extract Classes and Method Names
            elif isinstance(node, ast.ClassDef):
                method_names = [
                    subnode.name for subnode in node.body 
                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes[node.name] = method_names

            # Extract Direct Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)

            # Extract From Imports
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        return {
            "functions": functions,
            "classes": classes,
            "imports": sorted(list(imports)),
            "dependents": []  # Populated during recalculation step
        }

    def _recalculate_dependents(self, graph: Dict[str, Any]) -> None:
        """
        Maps which files import other files in the graph to calculate downstream impact radius.
        """
        # Clear existing dependents lists
        for module_data in graph.values():
            module_data["dependents"] = []

        # Compare imports against known module file paths
        for target_file, data in graph.items():
            for imported_mod in data.get("imports", []):
                # Convert module dot notation to relative file path (e.g., "modules.parsers" -> "modules/parsers")
                expected_path_prefix = imported_mod.replace(".", "/")

                for file_key in graph.keys():
                    if file_key != target_file and file_key.startswith(expected_path_prefix):
                        if target_file not in graph[file_key]["dependents"]:
                            graph[file_key]["dependents"].append(target_file)

    def _load_existing_graph(self) -> Dict[str, Any]:
        if self.graph_output_path.exists():
            try:
                return json.loads(self.graph_output_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_graph(self, graph: Dict[str, Any]) -> None:
        self.graph_output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to temporary file first then replace for atomic writing
        temp_path = self.graph_output_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
        temp_path.replace(self.graph_output_path)
