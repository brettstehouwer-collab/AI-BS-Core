import os
import shutil

root = r"C:\AI-BS"

dirs = {
    'output': os.path.join(root, 'output'),
    'installers': os.path.join(root, "InstallerEXE's"),
    'state': os.path.join(root, 'state'),
    'summaries': os.path.join(root, 'Agent_Handoff_Summaries'),
    'scratch': os.path.join(root, 'scratch'),
    'models': r"C:\AI-BS-Models\checkpoints"
}

for d in dirs.values():
    os.makedirs(d, exist_ok=True)

to_installers = [
    'Grass_7.4.4_x64-setup.exe', 'antigravity-sdk-python-main.zip', 'build_versioned.exe',
    'drive-download-20260717T004410Z-1-001.zip', 'drive-download-20260717T010128Z-1-001.zip',
    'earnapp-web-latest.apk', 'mainnet.2026-07-01.tar.gz.torrent', 'ollama.ollama-0.0.2.vsix'
]

to_output = [
    'ComfyUI_00004_.png', 'Room stage.jpg', 'bedroom.jpg', 'sample_00002_.png',
    'test_render.mp4', 'test_render_async.mp4'
]

to_state = [
    'auto_healer_daemon.pid', 'chroma_daemon.pid', 'context_ingestor_daemon.pid',
    'daemon_manager.lock', 'discord_bot_daemon.pid', 'drip_trader_daemon.pid',
    'memory_daemon.pid', 'minerwatch_daemon.pid', 'predictive_engine_daemon.pid',
    'research_agent_daemon.pid', 'researcher_daemon.pid', 'wallet_tracker_daemon.pid'
]

to_summaries = [
    'AI_BS_Chat_Log.md', 'AI_BS_Handover.md', 'AI_BS_Session_Summary_2026-07-23.md',
    'AI_BS_Session_Summary_2026-07-25.md', 'AI_BS_Task.md', 'AI_BS_Walkthrough.md',
    'Full_Chat_Transcript_2026-07-22.md', 'handoff.md', 'handoff_state.json', 'lh_issues.txt'
]

to_models = ['v1-5-pruned-emaonly-fp16.safetensors']

to_scratch = [
    'agent_state.py', 'ai_adapter.py', 'batch_run.py', 'calendar_init.py',
    'check_balance.py', 'check_balance_raw.py', 'check_history.py',
    'chroma_merge_collections.py', 'deploy_uncensored.py',
    'disk_image_manager_v2.py', 'extract_current.py', 'extract_takeout.py',
    'gcs_scanner.py', 'generate_matrix_spec.py',
    'grammar_engine.py', 'imagegen_agent.py', 'increment_frontend_version.py', 'infinite_learning_loop.py',
    'ingest_drives.py', 'ingest_local_vault.py', 'ingest_takeout.py',
    'ingest_windows_cmds.py', 'ingest_workspace_docs.py', 'local_imagegen.py',
    'matrix_docs.py', 'matrix_signer.py', 'memory_bank.py',
    'move_models.py', 'phase4_endpoints_v2.py',
    'predictive_engine.py', 'read_docx.py', 'reasoning_logger.py', 'run_dry.py',
    'save_chat.py', 'semantic_cache.py',
    'sequential_download.py', 'slack_integration_test.py', 'telemetry_checkpoint_db.py',
    'test_batch_output.py', 'test_batch_status.json', 'test_chat.py',
    'test_comfy.py', 'test_drip_trader.py', 'test_empty.py', 'test_integration.py',
    'test_ollama.py', 'test_pdf.py', 'test_pdf_import.py', 'test_phase4_simple.py',
    'test_phase4_stages_2_3.py', 'test_phase4_vm.py', 'test_purposeful_error.py',
    'test_query.py', 'test_unreal.py', 'test_vision.py', 'theatrical_event_bus.py',
    'vlc_stream_manager.py'
]

moves = [
    (to_installers, dirs['installers']),
    (to_output, dirs['output']),
    (to_state, dirs['state']),
    (to_summaries, dirs['summaries']),
    (to_models, dirs['models']),
    (to_scratch, dirs['scratch'])
]

moved_count = 0
for file_list, target_dir in moves:
    for filename in file_list:
        src = os.path.join(root, filename)
        if os.path.exists(src):
            dst = os.path.join(target_dir, filename)
            shutil.move(src, dst)
            moved_count += 1
            print(f"Moved {filename} -> {os.path.basename(target_dir)}")

print(f"\nSUCCESS: Organized and relocated {moved_count} loose files into target sub-directories.")
