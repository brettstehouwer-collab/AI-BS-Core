# AI-BS Sovereign Native Studio Comprehensive Audit Report

* Timestamp: `2026-10-14T15:27:36Z`
* Overall Verdict: `PASS`

## 1. Interactive Widget Sweep
* Tab and Stack Indices Traversed: `59`
* Buttons Discovered: `610`
* Buttons Clicked (Live Safe): `454`
* Buttons Dry Run Gated: `5`
* Buttons Auto Remediated: `13`
* Input Fields Exercised: `101 / 101`
* Combo Boxes Exercised: `34 / 35`
* Sliders Exercised: `15 / 15`
* Checkboxes Exercised: `18 / 18`
* Tables Discovered: `25`
* Lists Discovered: `10`
* Peak UI Dispatch Latency: `1736.74 ms`
* Unhandled Exceptions: `0`

## 2. Hardware Telemetry
* GPU Available: `True`
* GPU Model: `NVIDIA GeForce RTX 4090`
* GPU Temperature: `80 C`
* VRAM Used / Total: `10670.73 MB / 24564.0 MB`
* CPU Logical Cores: `32` (`46.7%` load)
* RAM Available / Total: `3.61 GB / 31.15 GB`
* WASAPI Output Endpoints: `1`

## 3. Daemon and Port Matrix
* Listening Ports: `11 / 20`
* FastAPI_Core (Port `8080`): Valid=`True`, Status=`200`, Latency=`1.83 ms`
* ComfyUI (Port `8189`): Valid=`False`, Status=`None`, Latency=`N/A ms`
* Ollama_Primary (Port `11434`): Valid=`True`, Status=`200`, Latency=`4.94 ms`
* Ollama_Secondary (Port `11435`): Valid=`True`, Status=`200`, Latency=`79.12 ms`
* ChromaDB (Port `8002`): Valid=`False`, Status=`None`, Latency=`N/A ms`
