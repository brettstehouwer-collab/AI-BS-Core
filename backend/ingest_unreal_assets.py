import sqlite3
import os

def infer_asset_type(path):
    lower_path = path.lower()
    if 'material' in lower_path:
        return 'Material'
    elif 'texture' in lower_path or 't_' in os.path.basename(lower_path):
        return 'Texture'
    elif 'mesh' in lower_path or 'sm_' in os.path.basename(lower_path):
        return 'StaticMesh'
    elif 'blueprint' in lower_path or 'bp_' in os.path.basename(lower_path):
        return 'Blueprint'
    elif 'audio' in lower_path or 'sound' in lower_path or 'a_' in os.path.basename(lower_path):
        return 'Audio'
    elif 'animation' in lower_path:
        return 'Animation'
    else:
        return 'Misc'

def main():
    txt_file = r"C:\AI-BS\all_unreal_assets.txt"
    db_file = r"C:\AI-BS\backend\unreal_assets.db"
    
    if not os.path.exists(txt_file):
        print(f"Error: {txt_file} not found.")
        return

    conn = sqlite3.connect(db_file)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type TEXT,
            asset_name TEXT,
            package_path TEXT,
            full_disk_path TEXT
        )
    ''')
    c.execute('DELETE FROM assets') # Clear existing

    # The file might be UTF-16 from powershell
    try:
        with open(txt_file, 'r', encoding='utf-16le') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    assets_to_insert = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('FullName') or line.startswith('--'):
            continue
            
        full_path = line
        filename = os.path.basename(full_path)
        name, ext = os.path.splitext(filename)
        
        # Approximate package path logic
        package_path = full_path
        if "Engine\\Content" in full_path:
            package_path = "/Engine/" + full_path.split("Engine\\Content\\")[1].replace("\\", "/").replace(".uasset", "").replace(".umap", "")
        elif "Megascans" in full_path:
            package_path = "/Megascans/" + name
        else:
            package_path = "/Vault/" + name

        asset_type = infer_asset_type(full_path)
        
        assets_to_insert.append((asset_type, name, package_path, full_path))

    c.executemany('INSERT INTO assets (asset_type, asset_name, package_path, full_disk_path) VALUES (?, ?, ?, ?)', assets_to_insert)
    conn.commit()
    print(f"Inserted {len(assets_to_insert)} assets into database.")
    
    # Create indexes for fast searching
    c.execute('CREATE INDEX IF NOT EXISTS idx_name ON assets(asset_name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_type ON assets(asset_type)')
    
    conn.close()

if __name__ == "__main__":
    main()
