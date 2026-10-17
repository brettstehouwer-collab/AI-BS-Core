import ast
import os
import re
import sqlite3
import time
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\AI-BS")
DB_PATH = WORKSPACE_ROOT / "backend" / "aibs_master.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_blast_radius_schema():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS blast_radius_nodes (
        node_id TEXT PRIMARY KEY,
        node_type TEXT NOT NULL, -- 'backend_route', 'router_module', 'frontend_component', 'shared_util'
        name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        metadata_json TEXT
    );

    CREATE TABLE IF NOT EXISTS blast_radius_edges (
        edge_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        relation TEXT NOT NULL, -- 'calls_api', 'imports', 'mounts_router', 'renders_component'
        weight REAL DEFAULT 1.0,
        FOREIGN KEY (source_id) REFERENCES blast_radius_nodes(node_id),
        FOREIGN KEY (target_id) REFERENCES blast_radius_nodes(node_id)
    );

    CREATE INDEX IF NOT EXISTS idx_edge_source ON blast_radius_edges(source_id);
    CREATE INDEX IF NOT EXISTS idx_edge_target ON blast_radius_edges(target_id);
    """)
    conn.commit()
    conn.close()


def scan_backend_routes():
    """Extracts FastAPI routes, methods, and router files via Python AST."""
    routers_dir = WORKSPACE_ROOT / "backend" / "routers"
    backend_main = WORKSPACE_ROOT / "backend" / "AI_BS_Backend.py"
    nodes = []
    edges = []

    files_to_scan = list(routers_dir.glob("*.py"))
    if backend_main.exists():
        files_to_scan.append(backend_main)

    for py_file in files_to_scan:
        rel_path = str(py_file.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
        mod_name = py_file.stem
        mod_node_id = f"mod:{mod_name}"

        nodes.append({
            "node_id": mod_node_id,
            "node_type": "router_module",
            "name": mod_name,
            "file_path": rel_path,
            "metadata_json": f'{{"file": "{py_file.name}"}}'
        })

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for deco in node.decorator_list:
                    # Catch @router.get("/..."), @app.post("/...")
                    if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute):
                        method = deco.func.attr.lower()
                        if method in ("get", "post", "put", "delete", "patch", "options", "head"):
                            if deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
                                route_path = deco.args[0].value
                                route_id = f"route:{method}:{route_path}"
                                nodes.append({
                                    "node_id": route_id,
                                    "node_type": "backend_route",
                                    "name": f"{method.upper()} {route_path}",
                                    "file_path": rel_path,
                                    "metadata_json": f'{{"function": "{node.name}", "method": "{method}", "path": "{route_path}"}}'
                                })
                                edges.append({
                                    "edge_id": f"{mod_node_id}->{route_id}",
                                    "source_id": mod_node_id,
                                    "target_id": route_id,
                                    "relation": "declares_route",
                                    "weight": 1.0
                                })
    return nodes, edges


def scan_frontend_calls():
    """Extracts frontend component imports and API fetch/axios calls."""
    fe_dir = WORKSPACE_ROOT / "frontend" / "src" / "components"
    nodes = []
    edges = []

    if not fe_dir.exists():
        return nodes, edges

    for jsx_file in fe_dir.glob("*.jsx"):
        rel_path = str(jsx_file.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
        comp_name = jsx_file.stem
        comp_node_id = f"comp:{comp_name}"

        nodes.append({
            "node_id": comp_node_id,
            "node_type": "frontend_component",
            "name": comp_name,
            "file_path": rel_path,
            "metadata_json": f'{{"file": "{jsx_file.name}"}}'
        })

        content = jsx_file.read_text(encoding="utf-8", errors="replace")

        # 1. Catch API calls: fetch(`/api/...`), fetch(`${BACKEND_URL}/api/...`), axios.post('/api/...')
        api_matches = re.findall(r'(?:fetch|axios\.(?:get|post|put|delete))\s*\(\s*[`\'"](?:\${(?:BACKEND_URL|API_BASE|BASE_URL)})?(/api/[a-zA-Z0-9_\-\/\{\}]+)', content)
        for route_path in set(api_matches):
            target_id_generic = f"route:api:{route_path}"
            edges.append({
                "edge_id": f"{comp_node_id}->call:{route_path}",
                "source_id": comp_node_id,
                "target_id": target_id_generic,
                "relation": "calls_api",
                "weight": 1.5
            })

        # 2. Catch Child Component Imports: import Foo from './Foo'
        import_matches = re.findall(r'import\s+([A-Za-z0-9_]+)\s+from\s+[\'"]\.\/([A-Za-z0-9_]+)[\'"]', content)
        for _, imp_name in import_matches:
            target_comp_id = f"comp:{imp_name}"
            edges.append({
                "edge_id": f"{comp_node_id}->import:{imp_name}",
                "source_id": comp_node_id,
                "target_id": target_comp_id,
                "relation": "renders_component",
                "weight": 1.0
            })

    return nodes, edges


def build_full_graph():
    init_blast_radius_schema()
    b_nodes, b_edges = scan_backend_routes()
    f_nodes, f_edges = scan_frontend_calls()

    conn = get_db()
    c = conn.cursor()

    all_nodes = {n["node_id"]: n for n in (b_nodes + f_nodes)}
    for edge in f_edges:
        if edge["target_id"].startswith("route:api:"):
            target_path = edge["target_id"].replace("route:api:", "")
            matched = False
            for nid, n in all_nodes.items():
                if n["node_type"] == "backend_route":
                    route_path = n["name"].split(" ")[-1]
                    if route_path == target_path or target_path.startswith(route_path):
                        edge["target_id"] = nid
                        matched = True
                        break
            if not matched:
                all_nodes[edge["target_id"]] = {
                    "node_id": edge["target_id"],
                    "node_type": "backend_route",
                    "name": target_path,
                    "file_path": "dynamic_or_external",
                    "metadata_json": "{}"
                }

    c.execute("DELETE FROM blast_radius_edges")
    c.execute("DELETE FROM blast_radius_nodes")

    for n in all_nodes.values():
        c.execute("""
            INSERT OR REPLACE INTO blast_radius_nodes (node_id, node_type, name, file_path, metadata_json)
            VALUES (?, ?, ?, ?, ?)
        """, (n["node_id"], n["node_type"], n["name"], n["file_path"], n["metadata_json"]))

    for e in (b_edges + f_edges):
        c.execute("""
            INSERT OR REPLACE INTO blast_radius_edges (edge_id, source_id, target_id, relation, weight)
            VALUES (?, ?, ?, ?, ?)
        """, (e["edge_id"], e["source_id"], e["target_id"], e["relation"], e.get("weight", 1.0)))

    conn.commit()
    node_count = c.execute("SELECT COUNT(*) FROM blast_radius_nodes").fetchone()[0]
    edge_count = c.execute("SELECT COUNT(*) FROM blast_radius_edges").fetchone()[0]
    conn.close()

    return {"status": "success", "nodes": node_count, "edges": edge_count}


def query_blast_radius(target_path_or_name: str, max_depth: int = 3) -> dict:
    r"""Calculates direct and transitive blast radius when a file, route, or component changes."""
    conn = get_db()
    c = conn.cursor()

    # Find matching node(s)
    clean_target = target_path_or_name.replace("\\", "/").strip().lstrip("/")
    c.execute("""
        SELECT node_id, node_type, name, file_path FROM blast_radius_nodes
        WHERE file_path LIKE ? OR name LIKE ? OR node_id LIKE ?
    """, (f"%{clean_target}%", f"%{clean_target}%", f"%{clean_target}%"))
    roots = [dict(r) for r in c.fetchall()]

    if not roots:
        conn.close()
        return {
            "target": target_path_or_name,
            "status": "not_found",
            "message": f"No node found matching '{target_path_or_name}' in dependency graph.",
            "impacted_components": [],
            "impacted_routes": []
        }

    visited = set()
    impacted_nodes = []
    queue = [(r["node_id"], 0) for r in roots]

    while queue:
        curr_id, depth = queue.pop(0)
        if curr_id in visited or depth > max_depth:
            continue
        visited.add(curr_id)

        # Look for reverse dependencies (who depends on or calls curr_id?)
        c.execute("""
            SELECT e.relation, e.source_id, n.node_type, n.name, n.file_path
            FROM blast_radius_edges e
            JOIN blast_radius_nodes n ON e.source_id = n.node_id
            WHERE e.target_id = ?
        """, (curr_id,))
        for row in c.fetchall():
            item = dict(row)
            if item["source_id"] not in visited:
                impacted_nodes.append({
                    "node_id": item["source_id"],
                    "node_type": item["node_type"],
                    "name": item["name"],
                    "file_path": item["file_path"],
                    "relation": item["relation"],
                    "depth": depth + 1
                })
                queue.append((item["source_id"], depth + 1))

        # Also look for forward dependencies (what will break downstream?)
        c.execute("""
            SELECT e.relation, e.target_id, n.node_type, n.name, n.file_path
            FROM blast_radius_edges e
            JOIN blast_radius_nodes n ON e.target_id = n.node_id
            WHERE e.source_id = ?
        """, (curr_id,))
        for row in c.fetchall():
            item = dict(row)
            if item["target_id"] not in visited:
                impacted_nodes.append({
                    "node_id": item["target_id"],
                    "node_type": item["node_type"],
                    "name": item["name"],
                    "file_path": item["file_path"],
                    "relation": item["relation"],
                    "depth": depth + 1
                })
                queue.append((item["target_id"], depth + 1))

    conn.close()

    impacted_components = [n for n in impacted_nodes if n["node_type"] == "frontend_component"]
    impacted_routes = [n for n in impacted_nodes if n["node_type"] == "backend_route"]
    impacted_modules = [n for n in impacted_nodes if n["node_type"] == "router_module"]

    risk_level = "LOW"
    total_impact = len(impacted_nodes)
    if total_impact > 10 or len(impacted_components) > 4:
        risk_level = "CRITICAL"
    elif total_impact > 4 or len(impacted_components) > 1:
        risk_level = "MEDIUM"

    return {
        "status": "success",
        "target": target_path_or_name,
        "matched_roots": roots,
        "risk_level": risk_level,
        "total_impacted_nodes": total_impact,
        "impacted_components": impacted_components,
        "impacted_routes": impacted_routes,
        "impacted_modules": impacted_modules
    }
