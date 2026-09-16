import os
import sys
import ast
import json

CHROMA_DB_MOCK_DIR = os.path.join(
    os.path.dirname(__file__), "chroma_db", "ast_snippets"
)
os.makedirs(CHROMA_DB_MOCK_DIR, exist_ok=True)


def shred_file(filepath):
    print(f"[AST Shredder] Analyzing {filepath}...")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code)

        snippets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Extract the exact string chunk of the function
                lines = code.splitlines()
                func_code = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                snippets.append(
                    {"name": node.name, "type": "function", "code": func_code}
                )
            elif isinstance(node, ast.ClassDef):
                lines = code.splitlines()
                class_code = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                snippets.append(
                    {"name": node.name, "type": "class", "code": class_code}
                )

        if snippets:
            db_path = os.path.join(
                CHROMA_DB_MOCK_DIR, f"{os.path.basename(filepath)}.json"
            )
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(snippets, f, indent=4)
            print(
                f"[AST Shredder] Shredded {len(snippets)} vectorized functions into ChromaDB Memory."
            )
        else:
            print(f"[AST Shredder] No functions or classes found to shred.")

    except SyntaxError:
        print(f"[AST Shredder] SyntaxError in {filepath}. Cannot parse AST.")
    except Exception as e:
        print(f"[AST Shredder] Error parsing AST: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bullshit_ast_shredder.py <filepath>")
        sys.exit(1)

    target_file = sys.argv[1]
    shred_file(target_file)
