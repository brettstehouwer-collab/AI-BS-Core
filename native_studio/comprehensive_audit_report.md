# AI-BS Sovereign Native Studio Comprehensive Audit Report

* Timestamp: `2026-10-14T19:51:45Z`
* Overall Verdict: `PASS`

## 1. Interactive Widget Sweep
* Tab and Stack Indices Traversed: `59`
* Buttons Discovered: `716`
* Buttons Clicked (Live Safe): `557`
* Buttons Dry Run Gated: `5`
* Buttons Auto Remediated: `1`
* Input Fields Exercised: `114 / 118`
* Combo Boxes Exercised: `41 / 42`
* Sliders Exercised: `21 / 21`
* Checkboxes Exercised: `20 / 20`
* Tables Discovered: `25`
* Lists Discovered: `10`
* Peak UI Dispatch Latency: `1840.78 ms`
* Unhandled Exceptions: `0`

## 2. Hardware Telemetry
* GPU Available: `True`
* GPU Model: `NVIDIA GeForce RTX 4090`
* GPU Temperature: `30 C`
* VRAM Used / Total: `10601.12 MB / 24564.0 MB`
* CPU Logical Cores: `32` (`40.7%` load)
* RAM Available / Total: `4.43 GB / 31.15 GB`
* WASAPI Output Endpoints: `3`

## 3. Daemon and Port Matrix
* Listening Ports: `18 / 25`
* FastAPI_Core (Port `8080`): Valid=`True`, Status=`200`, Latency=`3.46 ms`
* ComfyUI (Port `8189`): Valid=`True`, Status=`200`, Latency=`9.17 ms`
* Ollama_Primary (Port `11434`): Valid=`True`, Status=`200`, Latency=`87.03 ms`
* Ollama_Secondary (Port `11435`): Valid=`True`, Status=`200`, Latency=`65.86 ms`
* ChromaDB (Port `8002`): Valid=`True`, Status=`410`, Latency=`20.39 ms`
