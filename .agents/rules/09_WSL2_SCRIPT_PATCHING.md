# WSL2 Script Patching over Dual-Booting Standard

**Status:** ACTIVE & MANDATORY DIRECTIVE  
**Classification:** Virtualization & Host Systems Engineering  

## Directives
1. **Single Host Standard:** Never recommend dual-booting Ubuntu or setting up a separate Linux partition to solve WSL2 compatibility issues. The host environment remains strictly Windows 11 with WSL2.
2. **Aggressive Script Hacking:** When Linux-native installer scripts (like Vast.ai or Clore.ai) fail in WSL2 due to hardware visibility (e.g., `lspci` failing) or network constraints, your primary approach MUST be to patch and hack the bash scripts to bypass those checks, override subnets, and force execution inside WSL2.
3. **Native Windows Orchestration:** Rely on the custom AI-BS Windows Python/Go daemons (e.g., `aibs_gpu_worker_daemon.py`, Graceful Rejection Engine) to safely manage hardware state and prevent crashes caused by these WSL2 containers.
4. **Ledger Verification:** Always consult `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` before making architectural assumptions, as it contains the exact history of which scripts have already been patched and successfully deployed.
