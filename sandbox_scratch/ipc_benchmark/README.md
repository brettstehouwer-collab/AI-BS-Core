# AI-BS Polyglot IPC & Shared Memory Benchmark Suite

> **Location:** `C:\AI-BS\sandbox_scratch\ipc_benchmark\`  
> **Target Latency:** < 100 nanoseconds per message passing loop  
> **Supported Runtimes:** Go (`go-core`), C/C++, Rust, Zig  

## 🚀 Purpose
Isolated micro-benchmark environment for testing zero-overhead C-ABI FFI and Shared Memory (Ring Buffer) inter-process communication before integrating low-level state managers into production daemons.

## 📂 Benchmark Layout
- `README.md`: Overview & execution instructions.
- `ipc_shm_benchmark.go`: Go consumer testing Windows Shared Memory (`CreateFileMappingW` / `MapViewOfFile`).
- `ipc_shm_producer.c`: C-ABI reference producer for high-frequency shared memory ring buffer operations.
- `build_and_run.bat`: Windows compilation and execution script.
