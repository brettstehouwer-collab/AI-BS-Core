# Read-only findings for AI-BS

Branch `codex/audit-v532976-20261031`. Evidence refers to working-copy lines, including existing unstaged edits. Inspection used file reads and Git queries only. No application modules were imported, no tests ran, and no service or trading account was contacted.

## Verified in code

### Health and daemon contracts

- **GET /health, /api/health and /v1/health** share one handler. The success object has status ("online"), service ("AI-BS Central Cognitive Engine API"), process_id (integer), local_maintenance_protocol (1), gpu_accelerated (literal true), daemons (object mapping managed names to booleans), and timestamp (Unix seconds from time.time()). The daemon flag uses a process handle where available. The GPU field is a constant. See backend/AI_BS_Backend.py lines 2663–2713.
- **GET /api/executive/daemons** delegates to get_full_ecosystem_status. Its exact top-level fields are version, timestamp, online_ports, total_ports, online_count, total_services, active_count, total_count, ports, daemons, hardware, and registered_daemons_count. The timestamp is Unix seconds sampled after the port sweep and hardware collection. The three online counters share a value, as do the three totals. Each ports row contains port, name, tier, category, status (ONLINE/OFFLINE), pid, process_name, memory_mb, supervised, and daemon_name. Each daemons row contains port, name and status (running/standby). Hardware contains cpu_percent, ram_percent and gpu with vram_used_mb, vram_total_mb, name and temp_c. See backend/AI_BS_Backend.py lines 6310, 7147–7153 and 7231, and backend/core/daemon_manager.py lines 323–345 and 403–439.
- **GET /api/executive/status** returns status, engine, privileges, supported_command_types, host_platform and default_cwd without a timestamp (backend/AI_BS_Backend.py lines 6759–6785). **GET /system/status** returns gitStatus, ssdRamFootprint and activeAgents without a timestamp (lines 11929–11978).
- **GET /api/system/health** returns status, cpu_usage_percent, ram {used_gb,total_gb,percent}, gpu and storage {output_path,free_gb,total_gb,percent_used}. GPU fields depend on the telemetry branch. **GET /api/system/ports/status** returns status and ports [{port,name,online,status}]. Neither handler adds an observation time. See backend/routers/system_router.py lines 11, 37–81 and 88–103.
- **GET /api/media/health** returns {status,engine,details} on success, {status,engine,error} on exception, or {status} on other upstream responses. **GET /api/photo-studio/health** returns status, client_id, engine, active_provider, cuda_accelerated, model_name, telemetry and comfyui_loopback_online. **GET /api/security/health** returns status, ecosystem_version, rate_limiter, defensive_headers, cors_policy and inference_privacy. None adds a top-level timestamp. Nested provider payloads may vary. See backend/routers/media_router.py lines 41–53, photo_studio.py lines 98–132 and security_router.py lines 14–39.
- The route inventory below records additional domain-specific handlers and their return expressions. A returned variable, provider call or dictionary expansion identifies a dynamic portion of the response. Timestamp presence for an opaque provider payload is undetermined from its handler. Route declarations establish source contracts only. Copied router modules are identified by filename and are not evidence of a second mounted route.

### Chat commands and media intent

- **/status** performs an authenticated GET to /api/executive/daemons, parses JSON, prefers active_count/total_count and daemons, and falls back to online_ports/total_ports and ports. It labels running or ONLINE entries online and all others standby. It hardcodes the monitored-port count as 20 and also uses 20 as the missing-count fallback. It does not check res.ok before interpreting JSON and does not display timestamp. See frontend/components/ChatTab.jsx lines 4200–4235.
- **/health and /doctor** POST to /api/tools/execute with tool_name get_ecosystem_health and component all. The normal envelope is {status:"success",result:{status:"success",hardware,diagnostics}}. The UI selects diagnostics, then hardware, then stringified result. The tool envelope adds no timestamp. The GET to /api/health at line 4165 is a different path, the no-pending-operation branch of /backend status. See frontend/components/ChatTab.jsx lines 4158–4171 and 6637–6667, backend/AI_BS_Backend.py lines 6211–6228, and backend/tools/tool_registry.py lines 4380–4390.
- **Media status** is also distinct from the literal /service slash command, which invokes manage_ecosystem_service (ChatTab.jsx lines 6670–6683). resolve_media_status validates the current prompt, allows a film reply in eligible modes, classifies media intent, then probes ComfyUI for a status question. Its probe distinguishes running (including port), offline and unverified. The resolver returns a newline-terminated human-readable string or None. No observation time is attached. The router wraps the string in JSON or SSE, and the OpenAI-style path wraps it in message or delta choices. See backend/core/media_intent_policy.py lines 120–160 and 163–207, backend/routers/chat_router.py lines 176–183 and backend/AI_BS_Backend.py lines 8909–8911 and 9074–9085.

### Uncommitted overlap

Git diff --stat for the four named paths reports 197 insertions and 41 deletions. The cached diff for those paths is empty.

| Working-copy file | Added / removed | Existing edits |
|---|---:|---|
| backend/AI_BS_Backend.py | 14 / 1 | Registers driver portal, chat films, personal payments and ledger routes, expands CORS request headers and maps unavailable tool results to HTTP 503. The tool-execution route used by /health overlaps. Root health and executive daemon handler bodies are outside the diff. |
| backend/core/media_intent_policy.py | 5 / 0 | Inserts film-intent dispatch before media classification in resolve_media_status. The ComfyUI probe-result formatting block is outside the diff. |
| frontend/App.jsx | 99 / 14 | Changes local desktop admin session initialization, authentication and sign-out handling, and brand campaign component/navigation wiring. |
| frontend/components/ChatTab.jsx | 79 / 26 | Changes coding-mode UI, stream frame parsing and metadata rendering, conversation/draft state handling, message history and focus. The /status and /health command blocks are outside the changed hunks. |

### Trading paths with offline test seams

- **Execution and failover.** scratch/ha_execution_gateway.py line 1271 defines ExecutionGateway. tests/ha/test_ha_fault_matrix.py lines 55–128 implement an in-memory FakeExchange with synthetic books, balances, order acknowledgements, cancellation, mutation recording and simulated lost responses. Lines 132–145 construct a temporary SQLite AuthorityStore, FakeClock and ExecutionGateway(store, fake_exchange). That fixture exercises the gateway without an authenticated exchange client. This finding applies to the cited fixture, not every test in the module.
- **Strategy calculations.** backend/modules/crypto_backtest_sandbox.py lines 55–64, 86 and 210–212 accept an explicit database path and input price series and record simulation results locally. tests/test_commercial_and_crypto_expansion.py lines 54–83 supply synthetic prices and a tmp_path database and assert simulation-only execution. Even this offline test writes its temporary database if run.
- **Historical context.** AGENTS.md lines 3–21 describe previous synthetic checks and held orders. PROJECT.md describes the application architecture. TEST_INFRA.md lines 3–5 describe E2E tests using processes and HTTP. Those documents do not establish that an arbitrary E2E test is offline.

## Inferred

For a freshness indicator on /status, the smallest change is at ChatTab.jsx lines 4206–4209. Format the existing numeric timestamp as epoch seconds, converting to milliseconds for JavaScript Date, and render an absolute check time. A missing or invalid value should display as unknown. For the ComfyUI conversational reply, the common insertion point is immediately after the awaited probe and before the return at media_intent_policy.py lines 181–189. Adding a UTC check time to that text would reach both streaming and non-streaming consumers. A machine-readable field would require a separate adapter contract decision.

## Decisions requested

Choose whether the first change covers only /status or also the Matrix Doctor and ComfyUI replies. An absolute check time needs no expiry policy. If a fresh/stale badge is required, specify the maximum age and whether old chat messages must update as they age.

## Additional route evidence

The entries below use router-local prefixes where declared. They include status mutations and job-specific status because these also match the requested paths. Literal return objects show their keys directly. Delegated returns retain the source expression; the exact runtime body and timestamp fields of those delegates have not all been independently established.

#### GET /api/learning-loop/status (line 2196)

backend/AI_BS_Backend.py, handler `root_learning_loop_status`.

- Line 2202 returns `learning_loop_instance.get_status()`.

#### GET /api/audio/aes3-status (line 2438) · GET /audio/aes3-status (line 2440)

backend/AI_BS_Backend.py, handler `api_get_aes3_status`.

- Line 2450 returns `telemetry`.

#### GET /api/health (line 2663) · GET /health (line 2665) · GET /v1/health (line 2667)

backend/AI_BS_Backend.py, handler `root_health`.

- Line 2697 returns `{'status': 'online', 'service': 'AI-BS Central Cognitive Engine API', 'process_id': os.getpid(), 'local_maintenance_protocol': 1, 'gpu_accelerated': True, 'daemons': daemons_status, 'timestamp': time.time()}`.

#### GET /api/v1/emails/oauth-status (line 4493)

backend/AI_BS_Backend.py, handler `get_oauth_status`.

- Line 4615 returns `{'status': 'success', 'data': status_data}`.

#### GET /api/context/status (line 5431)

backend/AI_BS_Backend.py, handler `get_context_ingest_status`.

- Line 5449 returns `data`.
- Line 5453 returns `{'status': 'Error reading manifest', 'error': str(e)}`.
- Line 5455 returns `{'status': 'Manifest pending', 'total_files': 0, 'grabbed_files': []}`.

#### GET /api/trainer/status (line 6027)

backend/AI_BS_Backend.py, handler `trainer_status`.

- Line 6031 returns `{'status': 'active', 'trainer': 'BullshitTrainer', 'active_jobs': 0, 'gpu_utilization': '14%'}`.

#### GET /api/git/status (line 6037)

backend/AI_BS_Backend.py, handler `git_status_endpoint`.

- Line 6041 returns `{'branch': 'main', 'clean': True, 'modified_files': [], 'ahead': 0}`.

#### GET /telemetry/status (line 6155)

backend/AI_BS_Backend.py, handler `get_telemetry`.

- Line 6175 returns `JSONResponse(content=engine_telemetry)`.

#### GET /api/executive/status (line 6759)

backend/AI_BS_Backend.py, handler `get_executive_status`.

- Line 6765 returns `{'status': 'online', 'engine': 'AI-BS Executive IDE Controller', 'privileges': 'root_host_unrestricted', 'supported_command_types': ['powershell', 'cmd', 'wsl', 'python', 'node', 'ts', 'go', 'rust', 'cpp', 'c', 'sql', 'tool', 'build_project', 'file_read', 'file_write', 'file_rename', 'show_in_explorer', 'auto_heal'], 'host_platform': sys.platform, 'default_cwd': 'C:\\AI-BS'}`.

#### GET /api/executive/mobile-workstation/status (line 6931)

backend/AI_BS_Backend.py, handler `get_mobile_workstation_state`.

- Line 6939 returns `get_mobile_workstation_status()`.

#### GET /api/executive/wireless-cast/status (line 6999)

backend/AI_BS_Backend.py, handler `get_wireless_cast_state`.

- Line 7007 returns `get_wireless_cast_status()`.

#### GET /api/executive/privilege-directive/status (line 7097)

backend/AI_BS_Backend.py, handler `get_privilege_directive_state`.

- Line 7105 returns `get_sovereign_privilege_status()`.

#### GET /api/executive/daemons (line 7147)

backend/AI_BS_Backend.py, handler `get_executive_daemons`.

- Line 7153 returns `daemon_supervisor.get_full_ecosystem_status()`.

#### GET /api/mission/hardware-health (line 7551)

backend/AI_BS_Backend.py, handler `hardware_health_endpoint`.

- Line 7557 returns `res`.

#### GET /api/git/system/status (line 7627) · POST /api/git/system/status (line 7629)

backend/AI_BS_Backend.py, handler `git_system_status_suite`.

- Line 7633 returns `{'branch': 'main', 'clean': True, 'modified_files': [], 'ahead': 0}`.

#### GET /api/compute/status (line 8360)

backend/AI_BS_Backend.py, handler `get_compute_status_endpoint`.

- Line 8364 returns `{'status': 'online', 'gpu_name': 'NVIDIA GeForce RTX 4090', 'vram_used_mb': 4096, 'vram_total_mb': 24576, 'gpu_utilization_pct': 14.5, 'temperature_c': 42.0, 'power_draw_w': 85.0, 'active_jobs': 0}`.

#### GET /api/mining/status (line 8386)

backend/AI_BS_Backend.py, handler `get_mining_status_endpoint`.

- Line 8390 returns `{'status': 'active', 'hashrate_mhs': 0.0, 'pool': 'stratum+tcp://local-proxy:4444', 'power_limit_w': 250, 'temperature_c': 42.0, 'alerts': []}`.

#### GET /api/wallet/status (line 8408)

backend/AI_BS_Backend.py, handler `get_wallet_status_endpoint`.

- Line 8414 returns `{'status': 'online', 'wallet_status': 'synced', 'network': 'mainnet', 'synced_blocks': 892040, 'peer_count': 8}`.

#### GET /comfyui/status (line 11671)

backend/AI_BS_Backend.py, handler `comfyui_status`.

- Line 11703 returns `{'status': 'online', 'gpu': gpu, 'vram_total': vram_total, 'vram_free': vram_free}`.
- Line 11715 returns `{'status': 'offline'}`.
- Line 11719 returns `{'status': 'offline'}`.

#### GET /system/status (line 11929)

backend/AI_BS_Backend.py, handler `system_status`.

- Line 11961 returns `{'gitStatus': git_status, 'ssdRamFootprint': f'{os.path.getsize(MASTER_MEMORY_PATH) / 1024:.2f} KB' if os.path.exists(MASTER_MEMORY_PATH) else '0 KB', 'activeAgents': ['Trainer Daemon', 'Memory Offloader']}`.

#### GET /api/v1/pearl/status (line 13903)

backend/AI_BS_Backend.py, handler `get_pearl_status`.

- Line 13927 returns `{'status': 'stopped_by_user' if stopped_by_user else watchdog_data.get('status', 'unknown'), 'user_stopped': stopped_by_user, 'details': watchdog_data}`.

#### GET /api/v1/ecosystem/watchdog/status (line 13941)

backend/AI_BS_Backend.py, handler `get_watchdog_status`.

- Line 13953 returns `json.loads(status_file.read_text(encoding='utf-8'))`.
- Line 13957 returns `{'error': str(e)}`.
- Line 13959 returns `{'status': 'initializing'}`.

#### PATCH /api/calendar/tasks/{task_id}/status (line 454)

backend/routers/calendar_tasks_router.py, handler `update_task_status`.

- Line 469 returns `{'status': 'success', 'id': task_id, 'new_status': status}`.

#### POST /api/v1/chef/order/{order_id}/status (line 392)

backend/routers/chef_orders_router.py, handler `update_order_status`.


#### GET /api/comfyui/status/{prompt_id} (line 82)

backend/routers/comfyui_router.py, handler `check_status`.

- Line 86 returns `chained_jobs.get(prompt_id, {'status': 'pending'})`.
- Line 90 returns `{'status': 'pending'}`.
- Line 107 returns `{'status': 'completed', 'outputs': outputs}`.
- Line 109 returns `{'status': 'pending'}`.

#### GET /industry/status (line 33)

backend/routers/demo_industry_suites.py, handler `get_status`.

- Line 35 returns `{'status': 'Enterprise Industry OS backend is online and serving live telemetry from 70 SQLite databases.'}`.

#### GET /api/drop-sniffer/status (line 20)

backend/routers/drop_sniffer_router.py, handler `get_sniffer_status`.

- Line 24 returns `{'status': 'STOPPED', 'message': 'Heartbeat file not found.', 'is_alive': False}`.
- Line 35 returns `data`.

#### GET /api/v1/emails/status (line 236) · GET /api/v1/emails/config-status (line 237)

backend/routers/email_client_router.py, handler `get_email_status`.

- Line 272 returns `{'status': 'success', 'domain': creds['BUSINESS_DOMAIN'], 'primary_account': 'brett@stehouwer-publishing.com', 'relay_user': imap_user or 'Not Configured', 'has_app_password': has_app_pwd, 'imap_status': {'host': creds['IMAP_HOST'], 'port': creds['IMAP_PORT'], 'connected': imap_connected, 'error': imap_error}, 'smtp_status': {'host': creds['SMTP_HOST'], 'port': creds['SMTP_PORT'], 'ready': bool(imap_user and has_app_pwd)}, 'mailbox_stats': {'total_cached': len(cached), 'unread_inbox': unread_count, 'sent': sent_count, 'trash': trash_count, 'last_sync': last_sync_time}}`.

#### GET /api/v1/executive/matrix/status (line 450)

backend/routers/executive_cockpit_router.py, handler `get_matrix_status_endpoint`.

- Line 510 returns `{'status': 'healthy', 'timestamp': time.time(), 'elapsed_ms': elapsed_ms, 'autonomy_mode': executive_dispatcher.get_autonomy_mode(), 'pillars': {'media_studio': media_status, 'broadcast_kernel': broadcast_state, 'crypto_swarm': crypto_status, 'ollama_swarm': {'status': ollama_status, 'port': 11434, 'models_count': len(ollama_models), 'models_sample': ollama_models[:5]}, 'salad_engine': salad_data}, 'hardware': {'gpu_name': 'NVIDIA GeForce RTX 4090 (24GB)', 'temp_c': gpu_telem.get('temp_c', 0), 'vram_used_mb': gpu_telem.get('vram_used_mb', 0), 'vram_total_mb': gpu_telem.get('vram_total_mb', 24576), 'vram_free_mb': gpu_telem.get('vram_free_mb', 24576), 'gpu_util_pct': gpu_telem.get('gpu_util_pct', 0), 'ram_used_gb': round(v_mem.used / 1024 ** 3, 2), 'ram_total_gb': round(v_mem.total / 1024 ** 3, 2), 'ram_percent': v_mem.percent, 'disk_free_gb': round(disk.free / 1024 ** 3, 2), 'disk_total_gb': round(disk.total / 1024 ** 3, 2), 'disk_percent': disk.percent}, 'salad': salad_data, 'vault': vault_stats}`.

#### GET /api/v1/executive/sentinel/status (line 593)

backend/routers/executive_cockpit_router.py, handler `get_sentinel_status_endpoint`.

- Line 596 returns `{'status': 'success', 'engine': sentinel_engine.get_status()}`.

#### GET /api/v1/executive/cloud/status (line 627)

backend/routers/executive_cockpit_router.py, handler `get_cloud_status_endpoint`.

- Line 633 returns `{'status': 'success', 'gpu_sovereignty': cloud_burst_engine.get_status(), 'queue': cloud_burst_engine.get_queue()}`.

#### GET /api/v1/executive/voice/status (line 654)

backend/routers/executive_cockpit_router.py, handler `get_voice_status_endpoint`.

- Line 666 returns `{'status': 'ready', 'web_speech_api_available': True, 'f5_tts_eligible': f5_eligible, 'vram_free_mb': free_mb, 'gpu_temp_c': temp_c, 'governor_policy': 'HYBRID_ZERO_OVERHEAD_FALLBACK', 'active_mode': 'F5-TTS Neural Audio' if f5_eligible else 'Web Speech API (Zero-Overhead Hybrid Fallback)'}`.

#### GET /api/v1/fe-express/status (line 64)

backend/routers/fe_express_router.py, handler `get_status`.

- Line 78 returns `{'status': 'ONLINE', 'service': 'FE Express Box Truck Automation Hub', 'total_loads': total_loads, 'greenlight_loads': greenlights, 'alerts_dispatched': alerts_sent}`.

#### GET /api/media/health (line 41)

backend/routers/media_router.py, handler `get_media_engine_health`.

- Line 49 returns `{'status': 'online', 'engine': 'ComfyUI', 'details': data}`.
- Line 51 returns `{'status': 'offline', 'engine': 'ComfyUI', 'error': str(e)}`.
- Line 52 returns `{'status': 'offline'}`.

#### GET /api/memory-lab/status (line 135)

backend/routers/memory_lab_router.py, handler `get_memory_status`.

- Line 157 returns `{'status': 'success', 'attached': attached, 'pid': active_mem_mgr.pid if attached else None, 'process_name': active_mem_mgr.process_name if attached else None, 'base_address': hex(active_mem_mgr.base_address) if attached else '0x0', 'is_64bit': active_mem_mgr.is_64bit if attached else True, 'btd6_trainer': trainer_status}`.

#### GET /api/memory/status (line 82)

backend/routers/memory_router.py, handler `get_status_overview`.

- Line 85 returns `get_memory_bank_status()`.

#### GET /api/memory/learning-loop/status (line 87)

backend/routers/memory_router.py, handler `get_learning_loop_status`.

- Line 90 returns `learning_loop_instance.get_status()`.

#### GET /api/audio/assistant/status (line 488)

backend/routers/music_assistant_router.py, handler `music_assistant_status`.

- Line 502 returns `{'status': 'online', 'ollama_online': ollama_online, 'ollama_host': OLLAMA_HOST, 'available_models': available_models[:10], 'gpu_accelerated': True, 'demucs_bridge': 'online (RTX 4090)', 'vst_bridge': 'port_8013', 'capabilities': ['natural_language_daw_control', 'prompt_to_midi_generation', 'stem_isolation_orchestration', 'audio_repair_and_tuning_advice', 'harmonic_progression_synthesis', 'mix_and_fx_automation']}`.

#### GET /api/operations/gcp-status (line 690)

backend/routers/operations_audit_router.py, handler `get_gcp_status`.

- Line 698 returns `cached`.
- Line 713 returns `status`.

#### PUT /api/repair/tickets/{ticket_id}/status (line 217)

backend/routers/phone_repair_router.py, handler `update_ticket_status`.

- Line 229 returns `{'status': 'success', 'ticket': updated}`.

#### GET /api/photo-studio/health (line 98)

backend/routers/photo_studio.py, handler `get_health`.

- Line 123 returns `{'status': 'HEALTHY' if telemetry.get('status') == 'READY' else 'UNAVAILABLE', 'client_id': client_id, 'engine': 'LocalMattingEngine', 'active_provider': telemetry.get('active_provider'), 'cuda_accelerated': 'CUDA' in str(telemetry.get('active_provider')), 'model_name': telemetry.get('model_name'), 'telemetry': telemetry, 'comfyui_loopback_online': comfy_online}`.

#### PUT /api/powerwash/jobs/{job_id}/status (line 699)

backend/routers/power_washing_router.py, handler `update_job_status`.

- Line 707 returns `{'status': 'success', 'job_id': job_id, 'new_status': new_status}`.

#### GET /rag/status (line 188)

backend/routers/rag_bridge.py, handler `rag_status`.

- Line 190 returns `{'status': 'ChromaDB RAG Bridge online.', 'hot_db': HOT_DB_DIR, 'resource_db': RESOURCE_DIR, 'master_collection': 'ai_bs_synced_drive_assets'}`.

#### POST /api/v1/recdebut/athletes/update-status (line 1078)

backend/routers/rec_debut_router (2).py, handler `update_athletes_status`.

- Line 1083 returns `{'success': True, 'updated_count': 0}`.
- Line 1090 returns `{'success': True, 'updated_count': len(payload.athlete_ids), 'status': payload.status}`.

#### GET /api/v1/recdebut/broadcast/status (line 1431)

backend/routers/rec_debut_router (2).py, handler `get_broadcast_status`.

- Line 1441 returns `{'success': True, **state}`.

#### GET /api/v1/recdebut/scheduler/status (line 1452)

backend/routers/rec_debut_router (2).py, handler `get_scheduler_status`.

- Line 1457 returns `{'success': True, 'active': False, 'message': 'Scheduler state file not created yet.'}`.
- Line 1467 returns `{'success': True, 'scheduler_active': state.get('scheduler_active', True), 'next_batch_number': state.get('next_batch_number', 2), 'next_batch_scheduled_at': next_run, 'next_batch_scheduled_iso': state.get('next_batch_scheduled_iso'), 'countdown_seconds': diff, 'countdown_formatted': f'{hours}h {minutes}m {seconds}s', 'batch_size': state.get('batch_size', 400), 'interval_hours': 24, 'batches': state.get('batches', [])}`.

#### GET /api/v1/recdebut/quota-status (line 1855)

backend/routers/rec_debut_router (2).py, handler `get_daily_quota_status`.

- Line 1900 returns `{'success': True, 'sent_last_24h': sent_last_24h, 'daily_ceiling': daily_ceiling, 'remaining_today': remaining_today, 'pending_count': pending_count, 'total_contacted': total_contacted, 'total_athletes': total_athletes, 'athletes_with_emails': athletes_with_emails, 'recommended_batch_size': recommended_batch_size, 'days_to_complete': days_to_complete, 'swarm_accounts_count': len(active_swarm), 'swarm_daily_ceiling': total_swarm_daily_ceiling, 'swarm_remaining_today': swarm_remaining_today, 'swarm_days_to_complete': swarm_days_to_complete, 'status': 'READY' if remaining_today > 0 else 'DAILY_CAP_REACHED'}`.

#### GET /api/v1/recdebut/cloudflared/status (line 2756)

backend/routers/rec_debut_router (2).py, handler `get_cloudflared_status`.

- Line 2778 returns `{'success': True, 'tunnel_active': is_running, 'tunnel_pid': tunnel_pid, 'tunnel_url': 'https://api.brettstehouwer.live', 'tunnel_domain': 'api.brettstehouwer.live', 'account_id': '81041170430c35368afacc42e6efec67', 'zones': [{'domain': 'stehouwer-publishing.com', 'status': 'ready', 'email_routing': True}, {'domain': 'brettstehouwer.live', 'status': 'active', 'email_routing': False}], 'edge_routes': ['/api/v1/recdebut/cloudflared/send', '/api/v1/recdebut/broadcast', '/api/v1/recdebut/sms/replies', '/api/v1/recdebut/outreach-analytics'], 'supported_channels': ['sms_carrier_mms', 'html_email_tracked'], 'caller_id': {'name': 'Dennis Bell', 'phone': '+1-616-291-5227', 'email': 'dbell002@sbcglobal.net'}}`.

#### GET /api/v1/recdebut/status (line 3909) · GET /api/recdebut/status (line 3910)

backend/routers/rec_debut_router (2).py, handler `get_recdebut_status_endpoint`.

- Line 3918 returns `{'entity': 'Recreational Debut', 'status': 'ONLINE', 'athletes_in_db': athlete_count, 'coaches_in_db': coach_count, 'dispatches_sent': dispatch_count, 'edge_tunnel': 'https://api.brettstehouwer.live', 's25_ultra_apk_built': True, 'verification_numbers': ['+1-616-291-5227', '+1-616-402-3628']}`.

#### POST /api/v1/recdebut/athletes/update-status (line 2310)

backend/routers/rec_debut_router.py, handler `update_athletes_status`.

- Line 2320 returns `{'success': True, 'updated_count': 0}`.
- Line 2334 returns `{'success': True, 'updated_count': len(payload.athlete_ids), 'status': payload.status}`.

#### GET /api/v1/recdebut/broadcast/status (line 3018)

backend/routers/rec_debut_router.py, handler `get_broadcast_status`.

- Line 3038 returns `{'success': True, **state}`.

#### GET /api/v1/recdebut/scheduler/status (line 3060)

backend/routers/rec_debut_router.py, handler `get_scheduler_status`.

- Line 3070 returns `{'success': True, 'active': False, 'message': 'Scheduler state file not created yet.'}`.
- Line 3090 returns `{'success': True, 'scheduler_active': state.get('scheduler_active', True), 'next_batch_number': state.get('next_batch_number', 2), 'next_batch_scheduled_at': next_run, 'next_batch_scheduled_iso': state.get('next_batch_scheduled_iso'), 'countdown_seconds': diff, 'countdown_formatted': f'{hours}h {minutes}m {seconds}s', 'batch_size': state.get('batch_size', 400), 'interval_hours': 24, 'batches': state.get('batches', [])}`.

#### GET /api/v1/recdebut/quota-status (line 3869)

backend/routers/rec_debut_router.py, handler `get_daily_quota_status`.

- Line 3959 returns `{'success': True, 'sent_last_24h': sent_last_24h, 'daily_ceiling': daily_ceiling, 'remaining_today': remaining_today, 'pending_count': pending_count, 'total_contacted': total_contacted, 'total_athletes': total_athletes, 'athletes_with_emails': athletes_with_emails, 'recommended_batch_size': recommended_batch_size, 'days_to_complete': days_to_complete, 'swarm_accounts_count': len(active_swarm), 'swarm_daily_ceiling': total_swarm_daily_ceiling, 'swarm_remaining_today': swarm_remaining_today, 'swarm_days_to_complete': swarm_days_to_complete, 'status': 'READY' if remaining_today > 0 else 'DAILY_CAP_REACHED'}`.

#### GET /api/v1/recdebut/textbee/status (line 5562) · GET /api/recdebut/textbee/status (line 5564)

backend/routers/rec_debut_router.py, handler `get_textbee_gateway_status`.

- Line 5585 returns `{'connected': False, 'error': 'Missing TextBee credentials'}`.
- Line 5603 returns `{'connected': True, 'provider': 'textbee', 'device': dev_data}`.
- Line 5615 returns `{'connected': False, 'error': f'TextBee API returned HTTP {resp.status_code}'}`.
- Line 5619 returns `{'connected': False, 'error': str(e)}`.

#### GET /api/v1/recdebut/cloudflared/status (line 7201)

backend/routers/rec_debut_router.py, handler `get_cloudflared_status`.

- Line 7245 returns `{'success': True, 'tunnel_active': is_running, 'tunnel_pid': tunnel_pid, 'tunnel_url': 'https://api.brettstehouwer.live', 'tunnel_domain': 'api.brettstehouwer.live', 'account_id': '81041170430c35368afacc42e6efec67', 'zones': [{'domain': 'stehouwer-publishing.com', 'status': 'ready', 'email_routing': True}, {'domain': 'brettstehouwer.live', 'status': 'active', 'email_routing': False}], 'edge_routes': ['/api/v1/recdebut/cloudflared/send', '/api/v1/recdebut/broadcast', '/api/v1/recdebut/sms/replies', '/api/v1/recdebut/outreach-analytics'], 'supported_channels': ['sms_carrier_mms', 'html_email_tracked'], 'caller_id': {'name': 'Dennis Bell', 'phone': '+1-616-291-5227', 'email': 'dbell002@sbcglobal.net'}}`.

#### GET /api/v1/recdebut/status (line 9481) · GET /api/recdebut/status (line 9483)

backend/routers/rec_debut_router.py, handler `get_recdebut_status_endpoint`.

- Line 9505 returns `{'reply_privacy': reply_privacy, 'entity': 'Recreational Debut', 'status': 'ONLINE', 'athletes_in_db': athlete_count, 'coaches_in_db': coach_count, 'dispatches_sent': dispatch_count, 'edge_tunnel': 'https://api.brettstehouwer.live', 's25_ultra_apk_built': True, 'verification_numbers': ['+1-616-291-5227', '+1-616-402-3628']}`.

#### GET /api/screenplay/adapt/status (line 480)

backend/routers/screenwriting_router.py, handler `get_adaptation_status`.

- Line 485 returns `{'status': 'not_found', 'progress': 0}`.
- Line 486 returns `tasks[project_name]`.

#### GET /api/screenwriting/projects/{project_name}/audio/transcribe/status (line 2130)

backend/routers/screenwriting_router.py, handler `get_audio_transcription_status`.

- Line 2137 returns `get_transcription_status(project_name, owner=owner)`.

#### GET /api/security/health (line 14)

backend/routers/security_router.py, handler `get_security_health`.

- Line 17 returns `{'status': 'SECURE', 'ecosystem_version': '5.129.0', 'rate_limiter': limiter.get_telemetry(), 'defensive_headers': {'Content-Security-Policy': 'Active', 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'SAMEORIGIN', 'Referrer-Policy': 'strict-origin-when-cross-origin', 'Permissions-Policy': 'Active'}, 'cors_policy': {'mode': 'Restricted Whitelist', 'allowed_origins': ['https://ai-bs-dashboard.web.app', 'https://stehouwer-publishing.com', 'http://localhost:*', 'http://127.0.0.1:*']}, 'inference_privacy': '100% Local Air-Gapped GPU (RTX 4090)'}`.

#### GET /api/security/watchdog/status (line 61)

backend/routers/security_router.py, handler `get_watchdog_status`.

- Line 69 returns `{'status': 'success', 'alerts': alerts}`.
- Line 71 returns `{'status': 'error', 'message': str(e)}`.
- Line 72 returns `{'status': 'success', 'alerts': [], 'watchdog_state': 'ACTIVE_SECURE'}`.

#### GET /api/sentinel/status (line 30)

backend/routers/self_healing_router.py, handler `get_sentinel_status`.


#### GET /api/v1/seo/status (line 700)

backend/routers/sitemap_seo_router.py, handler `get_seo_telemetry`.

- Line 711 returns `{'status': 'operational', 'domain': DOMAIN_BASE, 'frameworks': {'xml_sitemap': f'{DOMAIN_BASE}/sitemap.xml', 'json_feed': f'{DOMAIN_BASE}/feed.json', 'json_ld': f'{DOMAIN_BASE}/schema.jsonld', 'openapi_yaml': f'{DOMAIN_BASE}/openapi.yaml'}, 'total_urls': len(nodes), 'total_indexed_images': total_images, 'total_indexed_videos': total_videos, 'sitemap_last_modified_timestamp': mtime, 'sitemap_last_modified_iso': datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).isoformat() if mtime else None, 'recent_pings': PING_LEDGER[-5:], 'namespaces': {'core': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'image': 'http://www.google.com/schemas/sitemap-image/1.1', 'video': 'http://www.google.com/schemas/sitemap-video/1.1'}}`.

#### GET /api/system/health (line 56)

backend/routers/system_router.py, handler `system_health`.

- Line 66 returns `{'status': 'healthy', 'cpu_usage_percent': cpu_percent, 'ram': {'used_gb': round((ram.total - ram.available) / 1024 ** 3, 2), 'total_gb': round(ram.total / 1024 ** 3, 2), 'percent': ram.percent}, 'gpu': gpu, 'storage': {'output_path': 'C:/AI-BS/output', 'free_gb': round(output_disk.free / 1024 ** 3, 2), 'total_gb': round(output_disk.total / 1024 ** 3, 2), 'percent_used': output_disk.percent}}`.

#### GET /api/system/ports/status (line 88)

backend/routers/system_router.py, handler `get_ports_live_status`.

- Line 103 returns `{'status': 'success', 'ports': statuses}`.

#### GET /api/trading/trial-status (line 90)

backend/routers/trading_router.py, handler `get_crypto_trial_status`.

- Line 116 returns `result`.

#### GET /api/trading/status (line 185)

backend/routers/trading_router.py, handler `get_trader_status`.

- Line 188 returns `{'status': 'held', 'engine': 'Crypto-Swarm Micro-Drip Engine', 'runtime_verified': False, 'execution': execution_status(), 'risk_limits_verified': False, 'max_drawdown_limit_pct': None, 'daily_trade_cap_usd': None}`.

#### GET /api/trading/kraken/status (line 257)

backend/routers/trading_router.py, handler `get_kraken_status`.

- Line 263 returns `kraken_service.get_status()`.
- Line 265 returns `{'status': 'error', 'message': str(e)}`.

#### GET /unreal/tracker/status (line 154)

backend/routers/unreal_bridge_new.py, handler `tracker_status`.

- Line 157 returns `{'status': 'success', 'running': is_running}`.

#### GET /unreal/status (line 185)

backend/routers/unreal_bridge_new.py, handler `unreal_status`.

- Line 187 returns `{'status': 'Unreal Engine Automation Bridge is Online.'}`.

#### GET /api/v1/unreal/status (line 75)

backend/routers/unreal_mcp_router.py, handler `get_unreal_status`.

- Line 81 returns `{'unreal_editor_running': is_proc_running, 'mcp_server_online': is_mcp_alive, 'mcp_url': DEFAULT_MCP_URL, 'engine_version': 'Unreal Engine 5.8', 'project_path': 'C:\\AI-BS\\UnrealHub\\AI_BS_Hub.uproject', 'recommended_action': 'ready' if is_mcp_alive else 'waiting_for_mcp' if is_proc_running else 'launch_required'}`.

#### GET /api/v1/updater/status (line 58)

backend/routers/updater_router.py, handler `get_updater_status`.

- Line 61 returns `{'status': 'online', 'current_version': CURRENT_VERSION, 'updater_stub_available': updater_bin is not None, 'updater_stub_path': updater_bin, 'base_directory': BASE_DIR, 'download_state': download_state}`.

#### GET /api/system/vram/status (line 27)

backend/routers/upgrades_router.py, handler `get_vram_status`.

- Line 30 returns `{'total_vram_gb': vram_orchestrator.total_vram_gb, 'used_vram_gb': vram_orchestrator.used_vram_gb, 'free_vram_gb': vram_orchestrator.free_vram_gb, 'allocations': vram_orchestrator.allocations, 'primary_model': vram_orchestrator.active_primary_model}`.

#### GET /api/video/batch_status/{job_id} (line 190)

backend/routers/video_router.py, handler `get_batch_status`.

- Line 194 returns `{'status': 'running', 'message': 'Starting batch worker...', 'current': 0, 'total': 1}`.
- Line 197 returns `json.load(f)`.
- Line 199 returns `{'status': 'running', 'message': 'Updating...', 'current': 0, 'total': 1}`.

#### GET /api/v1/wan-media/status/{prompt_id} (line 131)

backend/routers/wan_media_router.py, handler `check_media_status`.

- Line 137 returns `{'prompt_id': prompt_id, 'data': history.get(prompt_id, {})}`.

