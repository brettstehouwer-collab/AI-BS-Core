# AI-BS Sovereign Native Studio Comprehensive Audit Report

* Timestamp: `2026-10-15T18:57:56Z`
* Overall Verdict: `PASS`

## 1. Interactive Widget Sweep
* Tab and Stack Indices Traversed: `60`
* Buttons Discovered: `832`
* Buttons Clicked (Live Safe): `657`
* Buttons Dry Run Gated: `7`
* Buttons Auto Remediated: `21`
* Input Fields Exercised: `123 / 127`
* Combo Boxes Exercised: `54 / 55`
* Sliders Exercised: `45 / 45`
* Checkboxes Exercised: `28 / 28`
* Tables Discovered: `26`
* Lists Discovered: `10`
* Peak UI Dispatch Latency: `5842.49 ms`
* Unhandled Exceptions: `0`

## 2. Hardware Telemetry
* GPU Available: `True`
* GPU Model: `NVIDIA GeForce RTX 4090`
* GPU Temperature: `44 C`
* VRAM Used / Total: `24307.69 MB / 24564.0 MB`
* CPU Logical Cores: `32` (`84.9%` load)
* RAM Available / Total: `22.46 GB / 61.65 GB`
* WASAPI Output Endpoints: `1`

## 3. Daemon and Port Matrix
* Listening Ports: `23 / 25`
* FastAPI_Core (Port `8080`): Valid=`True`, Status=`200`, Latency=`3.5 ms`
* ComfyUI (Port `8189`): Valid=`True`, Status=`200`, Latency=`14.72 ms`
* Ollama_Primary (Port `11434`): Valid=`True`, Status=`200`, Latency=`137.78 ms`
* Ollama_Secondary (Port `11435`): Valid=`True`, Status=`200`, Latency=`123.49 ms`
* ChromaDB (Port `8002`): Valid=`True`, Status=`410`, Latency=`5.56 ms`
