import sqlite3, subprocess, time, datetime, psutil

DB_PATH = r'C:\AI-BS\backend\stehouwer_vault.db'

def get_net_bytes():
    net = psutil.net_io_counters()
    return net.bytes_recv, net.bytes_sent

def get_salad_process_clues():
    clues = []
    try:
        for p in psutil.process_iter(['name']):
            name = p.info.get('name', '').lower()
            if name in ['xmrig.exe', 'trex.exe', 'gminer.exe', 'nbminer.exe']:
                clues.append(name)
            elif 'vmmem' in name or 'wsl' in name:
                if "Docker/WSL Container" not in clues:
                    clues.append("Docker/WSL Container")
            elif 'ollama' in name:
                if "Ollama (AI)" not in clues:
                    clues.append("Ollama (AI)")
    except:
        pass
    return " + ".join(clues) if clues else "Unknown (Obfuscated)"

def insert_job(start, end, job_type, procs, dur, kwh, dl, ul, max_pwr, max_temp, peak_vram, peak_sys_ram, avg_cpu):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO salad_job_ledger (
                start_time, end_time, job_type, detected_process, duration_minutes,
                energy_kwh, network_dl_mb, network_ul_mb, max_gpu_power_w,
                max_gpu_temp_c, peak_vram_mb, peak_sys_ram_gb, avg_cpu_load_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'), job_type, procs, dur, kwh, dl, ul, max_pwr, max_temp, peak_vram, peak_sys_ram, avg_cpu))
        conn.commit()
        conn.close()
        print(f"[{datetime.datetime.now()}] Job logged: {job_type} | {dur:.1f} min | {kwh:.3f} kWh | {dl:.1f}MB DL")
    except Exception as e:
        print(f"Failed to log job: {e}")

print("God-Mode AI-BS Salad Ledger Daemon Starting...")

is_active = False
job_start_time = None
max_pwr = 0.0
max_temp = 0.0
peak_vram = 0.0
peak_sys_ram = 0.0
total_joules = 0.0
cpu_loads = []
detected_procs = set()
net_start_recv = 0
net_start_sent = 0
idle_strikes = 0
active_strikes = 0

POLL_INTERVAL = 10

while True:
    try:
        res = subprocess.run(['nvidia-smi', '--query-gpu=power.draw,temperature.gpu,utilization.gpu,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True)
        if res.returncode == 0:
            parts = res.stdout.strip().split(',')
            pwr = float(parts[0].strip())
            temp = float(parts[1].strip())
            util = float(parts[2].strip())
            vram = float(parts[3].strip())
            sys_ram_gb = psutil.virtual_memory().used / (1024**3)
            cpu_pct = psutil.cpu_percent(interval=None)
            
            # Hardware thresholds
            if util > 20 or pwr > 150 or cpu_pct > 30:
                active_strikes += 1
                idle_strikes = 0
            else:
                idle_strikes += 1
                active_strikes = 0
                
            # Job Starts
            if not is_active and active_strikes >= 2:
                is_active = True
                job_start_time = datetime.datetime.now()
                max_pwr = pwr
                max_temp = temp
                peak_vram = vram
                peak_sys_ram = sys_ram_gb
                total_joules = 0.0
                cpu_loads = [cpu_pct]
                detected_procs = set()
                net_start_recv, net_start_sent = get_net_bytes()
                print(f"[{job_start_time}] New Job detected! Tracking God-Mode metrics...")
                
            # Job Running
            elif is_active:
                max_pwr = max(max_pwr, pwr)
                max_temp = max(max_temp, temp)
                peak_vram = max(peak_vram, vram)
                peak_sys_ram = max(peak_sys_ram, sys_ram_gb)
                total_joules += pwr * POLL_INTERVAL
                cpu_loads.append(cpu_pct)
                
                clues = get_salad_process_clues()
                if clues != "Unknown (Obfuscated)":
                    for c in clues.split(" + "):
                        detected_procs.add(c)
                
                # Job Ends
                if idle_strikes >= 3:
                    job_end_time = datetime.datetime.now()
                    dur_min = (job_end_time - job_start_time).total_seconds() / 60.0
                    
                    net_end_recv, net_end_sent = get_net_bytes()
                    dl_mb = (net_end_recv - net_start_recv) / (1024**2)
                    ul_mb = (net_end_sent - net_start_sent) / (1024**2)
                    
                    kwh = (total_joules / 3600.0) / 1000.0
                    avg_cpu = sum(cpu_loads) / len(cpu_loads) if cpu_loads else 0.0
                    final_procs = " + ".join(detected_procs) if detected_procs else "Unknown (Obfuscated)"
                    
                    if peak_vram > 12000 or "Container" in final_procs:
                        job_type = "AI Container Workload"
                    elif "xmrig" in final_procs:
                        job_type = "CPU Crypto Mining"
                    elif peak_vram > 4000:
                        job_type = "GPU Crypto Mining"
                    else:
                        job_type = "Unknown Background Job"
                    
                    insert_job(job_start_time, job_end_time, job_type, final_procs, dur_min, kwh, dl_mb, ul_mb, max_pwr, max_temp, peak_vram, peak_sys_ram, avg_cpu)
                    
                    # Update the mobile web view
                    try:
                        subprocess.run(['python', r'C:\AI-BS\scripts\generate_ledger_html.py'])
                    except Exception as html_e:
                        print(f"Failed to update HTML view: {html_e}")
                    
                    is_active = False
            
            # --- ALWAYS output live telemetry state for the React Frontend ---
            try:
                import json
                telemetry_state = {
                    "is_active": is_active,
                    "gpu_utilization": util,
                    "gpu_power_w": pwr,
                    "gpu_temp_c": temp,
                    "vram_used_mb": vram,
                    "sys_ram_gb": sys_ram_gb,
                    "cpu_load_pct": cpu_pct,
                    "payout_bridge": {
                        "clore_balance": 1324.82,
                        "treasury_wallet": "0xd269c1CE398397b441F1D4573Bd630bDd6c1e56b",
                        "cryptocom_dest": "0x4761aD28A8A6b0F5F66E0825a03AA419376152aa"
                    },
                    "timestamp": datetime.datetime.now().isoformat()
                }
                with open(r'C:\AI-BS\frontend\public\telemetry.json', 'w') as tf:
                    json.dump(telemetry_state, tf)
            except Exception as e:
                pass
                    
    except Exception as e:
        pass
        
    time.sleep(POLL_INTERVAL)
