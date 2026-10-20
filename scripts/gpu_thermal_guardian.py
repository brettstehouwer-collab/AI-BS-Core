import subprocess, time, datetime

MAX_TEMP = 78
CRITICAL_TEMP = 82
TARGET_MAX_LIMIT = 600

print(f'[{datetime.datetime.now()}] AI-BS Thermal Guardian initialized. Active monitoring RTX 4090...')

while True:
    try:
        res = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=temperature.gpu,power.draw,utilization.gpu,power.limit', 
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True)
        if res.returncode == 0:
            parts = res.stdout.strip().split(',')
            temp = int(parts[0].strip())
            power = float(parts[1].strip())
            util = int(parts[2].strip())
            active_limit = float(parts[3].strip())
            
            # If critical, hard clamp immediately
            if temp >= CRITICAL_TEMP:
                subprocess.run(['nvidia-smi', '-pl', '350'])
                print(f'[{datetime.datetime.now()}] CRITICAL: Temp {temp}C! Hard clamping to 350W.')
            # If in danger zone, step down
            elif temp >= MAX_TEMP and active_limit > 350:
                new_limit = max(350, int(active_limit - 50))
                subprocess.run(['nvidia-smi', '-pl', str(new_limit)])
                print(f'[{datetime.datetime.now()}] WARNING: Temp {temp}C! Throttling limit down to {new_limit}W')
            # If load is high and temps are safe, ensure target limit is enforced
            elif temp < 74 and active_limit < TARGET_MAX_LIMIT:
                new_limit = min(TARGET_MAX_LIMIT, int(active_limit + 25))
                subprocess.run(['nvidia-smi', '-pl', str(new_limit)])
                print(f'[{datetime.datetime.now()}] Load {util}%, Temp {temp}C (Safe). Stepping up limit to {new_limit}W')
                
    except Exception as e:
        pass
    time.sleep(10)
