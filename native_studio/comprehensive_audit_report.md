# AI-BS Sovereign Native Studio Comprehensive Audit Report

* Timestamp: `2026-10-14T21:34:39Z`
* Overall Verdict: `PASS`

## 1. Interactive Widget Sweep
* Tab and Stack Indices Traversed: `60`
* Buttons Discovered: `727`
* Buttons Clicked (Live Safe): `564`
* Buttons Dry Run Gated: `5`
* Buttons Auto Remediated: `1`
* Input Fields Exercised: `115 / 119`
* Combo Boxes Exercised: `42 / 43`
* Sliders Exercised: `21 / 21`
* Checkboxes Exercised: `20 / 20`
* Tables Discovered: `25`
* Lists Discovered: `10`
* Peak UI Dispatch Latency: `1543.51 ms`
* Unhandled Exceptions: `0`

## 2. Hardware Telemetry
* GPU Available: `True`
* GPU Model: `NVIDIA GeForce RTX 4090`
* GPU Temperature: `30 C`
* VRAM Used / Total: `11687.98 MB / 24564.0 MB`
* CPU Logical Cores: `32` (`29.6%` load)
* RAM Available / Total: `2.98 GB / 31.15 GB`
* WASAPI Output Endpoints: `3`

## 3. Daemon and Port Matrix
* Listening Ports: `18 / 25`
* FastAPI_Core (Port `8080`): Valid=`True`, Status=`200`, Latency=`245.51 ms`
* ComfyUI (Port `8189`): Valid=`True`, Status=`200`, Latency=`80.99 ms`
* Ollama_Primary (Port `11434`): Valid=`True`, Status=`200`, Latency=`152.09 ms`
* Ollama_Secondary (Port `11435`): Valid=`True`, Status=`200`, Latency=`105.2 ms`
* ChromaDB (Port `8002`): Valid=`True`, Status=`410`, Latency=`1.86 ms`
