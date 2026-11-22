#!/usr/bin/env python3
import sys
import subprocess
import yaml

real_bin = "/usr/bin/nvidia-ctk.real"

args = sys.argv[1:]

if len(args) >= 2 and args[0] == "cdi" and args[1] == "generate":
    # Run real nvidia-ctk
    proc = subprocess.run([real_bin] + args, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)
    try:
        doc = yaml.safe_load(proc.stdout)
        if isinstance(doc, dict):
            doc["cdiVersion"] = "0.5.0"
            if "devices" in doc and isinstance(doc["devices"], list):
                # Check if device '0' is already present
                names = [d.get("name") for d in doc["devices"] if isinstance(d, dict)]
                if "0" not in names and len(doc["devices"]) > 0:
                    dev0 = dict(doc["devices"][0])
                    dev0["name"] = "0"
                    doc["devices"].insert(0, dev0)
            sys.stderr.write(proc.stderr)
            # Dump with clean yaml
            sys.stdout.write(yaml.dump(doc, sort_keys=False))
            sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"wrapper yaml error: {e}\n")
    # Fallback if parsing fails
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    sys.exit(proc.returncode)
else:
    # Passthrough
    res = subprocess.run([real_bin] + args)
    sys.exit(res.returncode)
