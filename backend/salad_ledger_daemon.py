import sqlite3, subprocess, time, datetime

DB_PATH = r'C:\AI-BS\backend\stehouwer_vault.db'

def insert_job(start, end, job_type, max_pwr, max_temp, peak_vram):
    dur = (end - start).total_seconds() / 60.0
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO salad_job_ledger (start_time, end_time, job_type, max_gpu_power_w, max_gpu_temp_c, peak_vram_mb, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'), job_type, max_pwr, max_temp, peak_vram, dur))
        conn.commit()
        conn.close()
        print(f"[{datetime.datetime.now()}] Job logged: {job_type} | {dur:.1f} min | {max_pwr}W Peak")
    except Exception as e:
        print(f"Failed to log job: {e}")

print("AI-BS Salad Ledger Daemon Starting...")

is_active = False
job_start_time = None
max_pwr = 0.0
max_temp = 0.0
peak_vram = 0.0
idle_strikes = 0
active_strikes = 0

while True:
    try:
        res = subprocess.run(['nvidia-smi', '--query-gpu=power.draw,temperature.gpu,utilization.gpu,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True)
        if res.returncode == 0:
            parts = res.stdout.strip().split(',')
            pwr = float(parts[0].strip())
            temp = float(parts[1].strip())
            util = float(parts[2].strip())
            vram = float(parts[3].strip())
            
            # Hardware thresholds for a job (AI or Crypto)
            if util > 20 or pwr > 150:
                active_strikes += 1
                idle_strikes = 0
            else:
                idle_strikes += 1
                active_strikes = 0
                
            # State Transitions
            if not is_active and active_strikes >= 2:
                # Job Started
                is_active = True
                job_start_time = datetime.datetime.now()
                max_pwr = pwr
                max_temp = temp
                peak_vram = vram
                print(f"[{job_start_time}] New Salad job detected! Tracking metrics...")
                
            elif is_active:
                # Update peak metrics
                max_pwr = max(max_pwr, pwr)
                max_temp = max(max_temp, temp)
                peak_vram = max(peak_vram, vram)
                
                if idle_strikes >= 3:
                    # Job Ended
                    job_end_time = datetime.datetime.now()
                    
                    # Classify job based on VRAM signature
                    job_type = "AI Container (High VRAM)" if peak_vram > 12000 else "Crypto Mining (Compute)"
                    
                    insert_job(job_start_time, job_end_time, job_type, max_pwr, max_temp, peak_vram)
                    
                    is_active = False
                    job_start_time = None
                    max_pwr = 0.0
                    max_temp = 0.0
                    peak_vram = 0.0
                    
    except Exception as e:
        pass
        
    time.sleep(10)
