#!/usr/bin/env python3
import sys
import os
import json
import subprocess

REAL_RUNC = "/usr/bin/runc.real"

args = sys.argv[1:]

# Find --bundle argument if present
bundle_path = None
for i, arg in enumerate(args):
    if arg == "--bundle" and i + 1 < len(args):
        bundle_path = args[i + 1]
        break
    elif arg.startswith("--bundle="):
        bundle_path = arg.split("=", 1)[1]
        break

if bundle_path:
    config_file = os.path.join(bundle_path, "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            
            modified = False
            linux = cfg.get("linux")
            if isinstance(linux, dict):
                resources = linux.get("resources")
                if isinstance(resources, dict):
                    block_io = resources.get("blockIO")
                    if isinstance(block_io, dict):
                        # Delete or zero out weight to prevent runc cgroup2 io.weight error in WSL2
                        if "weight" in block_io:
                            del block_io["weight"]
                            modified = True
                        if "leafWeight" in block_io:
                            del block_io["leafWeight"]
                            modified = True
                        if "weightDevice" in block_io:
                            del block_io["weightDevice"]
                            modified = True

            if modified:
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
        except Exception as e:
            # Fall back silently if parsing fails
            pass

# Execute real runc with all arguments
res = subprocess.run([REAL_RUNC] + args)
sys.exit(res.returncode)
