package main

import (
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"aibs_core/pkg/gateway"
	"aibs_core/pkg/supervisor"
)

func main() {
	log.Println("[AI-BS Engine] Starting initialization...")

	// Determine workspace root. Assuming we run from C:\AI-BS\go-core
	cwd, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get working directory: %v", err)
	}
	
	// If running inside go-core, rootDir is parent. If running from workspace root, rootDir is cwd.
	rootDir := cwd
	if filepath.Base(cwd) == "go-core" {
		rootDir = filepath.Dir(cwd)
	}
	backendDir := filepath.Join(rootDir, "backend")

	manager := supervisor.NewSupervisor()

	pythonExe := "python"
	customPython := filepath.Join(rootDir, "pyppeteer_env", "Scripts", "python.exe")
	if _, err := os.Stat(customPython); err == nil {
		pythonExe = customPython
	}

	chromaExe := "chroma"
	customChroma := filepath.Join(rootDir, "pyppeteer_env", "Scripts", "chroma.exe")
	if _, err := os.Stat(customChroma); err == nil {
		chromaExe = customChroma
	}
	manager.Register("chromadb_daemon", []string{chromaExe, "run", "--host", "0.0.0.0", "--port", "8001", "--path", filepath.Join(rootDir, "chroma_db")}, rootDir, true, true)
	manager.Register("ai_bs_backend", []string{pythonExe, filepath.Join(backendDir, "AI_BS_Backend.py")}, rootDir, true, true)
	manager.Register("memory_daemon", []string{pythonExe, filepath.Join(backendDir, "memory_daemon.py")}, rootDir, true, true)
	manager.Register("context_ingestor_daemon", []string{pythonExe, filepath.Join(backendDir, "context_ingestor_daemon.py")}, rootDir, true, true)
	manager.Register("researcher_daemon", []string{pythonExe, filepath.Join(backendDir, "research_agent_daemon.py")}, rootDir, true, true)
	
	// Register tracking / utility daemons (these will be ported entirely to Go in future phases)
	manager.Register("discord_bot_daemon", []string{pythonExe, filepath.Join(backendDir, "discord_bot_daemon.py")}, rootDir, true, true)
	manager.Register("wallet_tracker_daemon", []string{pythonExe, filepath.Join(backendDir, "wallet_tracker_daemon.py")}, rootDir, true, true)
	manager.Register("auto_healer_daemon", []string{pythonExe, filepath.Join(backendDir, "auto_healer_daemon.py")}, rootDir, true, true)
	
	// Register manual-only mining daemons
	manager.Register("gpu_miner", []string{pythonExe, filepath.Join(backendDir, "minerwatch_daemon.py")}, rootDir, true, false)
	manager.Register("chia_plotter", []string{pythonExe, filepath.Join(backendDir, "chia_plotter_daemon.py")}, rootDir, true, false)

	// Register Compute Monetization Scheduler
	manager.Register("gpu_scheduler", []string{pythonExe, filepath.Join(backendDir, "compute_monetization_daemon.py")}, rootDir, true, true)

	log.Println("[AI-BS Engine] Launching Supervisor...")
	manager.StartAll()

	log.Println("[AI-BS Engine] Starting Commercial Gateway (Port 8000)...")
	gw := gateway.NewGateway("8000", "8080", manager) // Go on 8000, Python on 8080
	go gw.StartServer()

	// Wait for termination signal (Ctrl+C, etc)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	<-sigChan
	log.Println("[AI-BS Engine] Termination signal received. Shutting down...")
	
	manager.StopAll()
	
	// Give processes a moment to clean up before exiting
	time.Sleep(1 * time.Second)
	log.Println("[AI-BS Engine] Shutdown complete.")
}
