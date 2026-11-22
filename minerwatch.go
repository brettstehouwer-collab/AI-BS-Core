package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// The structure that matches your AI-BS state expectation
type Telemetry struct {
	Timestamp string  `json:"timestamp"`
	Hashrate  float64 `json:"hashrate"`
	GPU_Temp  int     `json:"gpu_temp"`
	Status    string  `json:"status"`
}

func main() {
	fmt.Println("[AI-BS GOLANG DAEMON] MinerWatch Initialized. Awaiting telemetry...")

	// 1. Setup channel to listen for the "Tab Closed" kill signal from FastAPI
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// 2. Setup a high-frequency ticker (e.g., every 5 seconds)
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	cacheFile := "c:\\Users\\footb\\AI-BS\\state\\telemetry_cache.json"

	for {
		select {
		case <-ticker.C:
			// Simulated polling action
			data := Telemetry{
				Timestamp: time.Now().Format(time.RFC3339),
				Hashrate:  145.5, // Simulated TH/s
				GPU_Temp:  65,
				Status:    "OPTIMAL_STEHOUWER_REALITY",
			}

			file, _ := json.MarshalIndent(data, "", "  ")
			os.WriteFile(cacheFile, file, 0644)

		case <-sigChan:
			// Tab closed -> FastAPI sends SIGTERM -> Clean exit
			fmt.Println("[AI-BS GOLANG DAEMON] Termination signal received. Flushing and shutting down...")
			os.Exit(0)
		}
	}
}
