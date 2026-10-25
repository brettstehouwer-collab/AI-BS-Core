package main

import (
	"errors"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"aibs_core/pkg/gateway"
	"aibs_core/pkg/supervisor"
)

// Set by the release build; unstamped developer builds identify themselves honestly.
var buildVersion = "development"

type daemonStartupManager interface {
	StartAll()
	RestoreHandoff(string) error
}

// Gateway startup never claims or starts unrelated services by default.
func configureSupervision(manager daemonStartupManager, handoff string, manage bool) error {
	if handoff != "" && manage {
		return errors.New("-handoff and -manage-daemons cannot be combined")
	}
	if handoff != "" {
		return manager.RestoreHandoff(handoff)
	}
	if manage {
		manager.StartAll()
	}
	return nil
}

func main() {
	handoff := flag.String("handoff", "", "Restore verified running daemons from a handoff manifest; leave stopped entries stopped")
	checkHandoff := flag.Bool("check-handoff", false, "Validate the handoff without starting a listener or supervising processes")
	manageDaemons := flag.Bool("manage-daemons", false, "Explicitly start registered auto-start daemons; default is gateway only")
	showVersion := flag.Bool("version", false, "Print the compiled engine version without opening ports or managing services")
	flag.Parse()
	if *showVersion {
		fmt.Printf("AI-BS Engine %s\n", buildVersion)
		return
	}
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
	manager.Register("chromadb_daemon", []string{chromaExe, "run", "--host", "127.0.0.1", "--port", "8001", "--path", filepath.Join(rootDir, "chroma_db")}, rootDir, true, true)
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
	if *checkHandoff {
		if *handoff == "" {
			log.Fatal("[AI-BS Engine] -check-handoff requires -handoff")
		}
		if err := manager.ValidateHandoff(*handoff); err != nil {
			log.Fatalf("[AI-BS Engine] Handoff validation failed: %v", err)
		}
		log.Println("[AI-BS Engine] Handoff validated; no services changed.")
		return
	}

	// Reserve the gateway port before any process starts. A duplicate engine must
	// fail before it can launch duplicate background daemons.
	listener, err := net.Listen("tcp", "127.0.0.1:8000")
	if err != nil {
		log.Fatalf("[AI-BS Engine] Cannot reserve gateway port: %v", err)
	}
	log.Println("[AI-BS Engine] Applying explicit supervisor startup policy...")
	if err := configureSupervision(manager, *handoff, *manageDaemons); err != nil {
		listener.Close()
		log.Fatalf("[AI-BS Engine] Supervisor startup rejected: %v", err)
	}

	log.Println("[AI-BS Engine] Starting Commercial Gateway (Port 8000)...")
	gw := gateway.NewGateway("8000", "8080", manager) // Go on 8000, Python on 8080
	gw.Version = buildVersion
	go gw.Serve(listener)

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
