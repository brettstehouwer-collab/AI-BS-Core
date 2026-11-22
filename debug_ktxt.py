import sys, traceback
sys.path.append('/var/lib/vastai_kaalia/latest')
import ktxt_tojson

msg = open('/tmp/smi.xml').read()
try:
    res = ktxt_tojson.dispatch_nvidia_smi2_(msg)
    print("SUCCESS! Result length:", len(res))
    print(res[:300])
except Exception:
    traceback.print_exc()
