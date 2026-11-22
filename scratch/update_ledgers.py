import os, datetime, shutil, re

def update_ledgers():
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    date_no_dash = datetime.datetime.now().strftime('%Y%m%d')
    timestamp = datetime.datetime.now().astimezone().isoformat()
    
    # 1. Update Ecosystem Manual Version
    manual_path = r'C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md'
    new_version = '8.42.0'
    if os.path.exists(manual_path):
        with open(manual_path, 'r', encoding='utf-8') as f:
            manual_content = f.read()
        manual_content = re.sub(r'v8\.\d+\.\d+', f'v{new_version}', manual_content)
        with open(manual_path, 'w', encoding='utf-8') as f:
            f.write(manual_content)
            
        # Copy to artifacts
        artifact_name = f'{date_no_dash}_AI_BS_Master_Ecosystem_Manual_v{new_version}.md'
        artifact_path = os.path.join(r'C:\AI-BS\saved_data\artifacts', artifact_name)
        shutil.copy(manual_path, artifact_path)
        
        # Log to NotebookLM
        history_path = r'C:\AI-BS\NotebookLM_Records\artifact_history.md'
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, 'a', encoding='utf-8') as f:
            f.write(f'\n- {timestamp}: Updated Ecosystem Manual to v{new_version} and saved artifact {artifact_name}\n')

    # 2. Update Architectural Ledger
    ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
    entry = f'''
## Development Entry: {date_str} - Visual Data Vault Implementation (v{new_version})

### 1. Timestamped Development Entry & AI Rationale
**Timestamp:** {timestamp}
**Objective:** Create a visually beautiful, glassmorphic OSINT Data Vault to organize past and current webscans and searches.
**Rationale:** The user wanted to surface historical data searches (such as RapidAPI and Facebook scraped JSONs) via a fun, organized visual component. I added a new /api/vault/saved_data endpoint to the backend to scan the saved_data directory, dynamically categorize files based on their names, and serve them to the frontend. The OsintDataVaultTab was upgraded with modern glassmorphism UI, warning badges for failed scrapes, and an automatic fetch-and-merge process inside useAppStore.

### 2. Updated Technical Specifications
*   **Backend Vault API:** New GET /api/vault/saved_data route added in AI_BS_Backend.py that reads from C:\\AI-BS\\saved_data and parses raw JSON files.
*   **Frontend AppStore:** Extended useAppStore.js with etchPastSavedData() to hydrate osintVaultItems on mount.
*   **Visual Data Vault UI:** Completely refactored OsintDataVaultTab.jsx to leverage a g-black/30 backdrop-blur-xl grid, custom icons per OSINT source, error handling for faulty payload structures (e.g. item.data.message), and deep JSON preview slices.

### 3. Updated User Manual
AI_BS_MASTER_ECOSYSTEM_MANUAL.md bumped to v{new_version}.

### 4. Modified File List & Fallback Context
**Modified Files:**
- C:\\AI-BS\\backend\\AI_BS_Backend.py
- C:\\AI-BS\\frontend\\components\\useAppStore.js
- C:\\AI-BS\\frontend\\components\\OsintDataVaultTab.jsx

'''
    if os.path.exists(ledger_path):
        with open(ledger_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Insert after title
        insert_pos = content.find('\n## ')
        if insert_pos != -1:
            content = content[:insert_pos] + '\n' + entry + content[insert_pos:]
        else:
            content += entry
            
        with open(ledger_path, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == '__main__':
    update_ledgers()
