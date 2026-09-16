//go:build ignore

package main

import (
	"fmt"
	"net/http"
	"time"
)

func main() {
	fmt.Println("==================================================")
	fmt.Println(" AI-BS Go Gateway: 7-Pass Validation Suite ")
	fmt.Println("==================================================")

	targetURL := "http://127.0.0.1:8000"
	
	// Ensure the server has a second to start if we are running concurrently
	time.Sleep(1 * time.Second)

	passes := 0
	totalPasses := 7

	tests := []struct {
		Name     string
		Method   string
		Endpoint string
		Expected int
		IsCORS   bool
	}{
		{"Pass 1: Core Health Endpoint /api/health", "GET", "/api/health", 200, false},
		{"Pass 2: Legacy Health Endpoint /health", "GET", "/health", 200, false},
		{"Pass 3: Core Models Endpoint /api/models", "GET", "/api/models", 200, false},
		{"Pass 4: Legacy Models Endpoint /models", "GET", "/models", 200, false},
		{"Pass 5: Active Defense CORS Pre-Flight", "OPTIONS", "/api/health", 200, true},
		{"Pass 6: IPC Proxy ComfyUI Media Stub", "GET", "/api/comfy/media", 200, false},
		{"Pass 7: Invalid Route Handling", "GET", "/invalid-route", 404, false},
	}

	for _, t := range tests {
		req, _ := http.NewRequest(t.Method, targetURL+t.Endpoint, nil)
		
		if t.IsCORS {
			req.Header.Set("Origin", "https://stehouwer-publishing.com")
			req.Header.Set("Access-Control-Request-Method", "GET")
		} else {
			// Simulate a valid Firebase API Key for non-CORS preflight requests
			req.Header.Set("X-API-Key", "simulated_firebase_key")
		}

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			fmt.Printf("❌ %s : FAILED (Connection Error: %v)\n", t.Name, err)
			continue
		}
		
		if resp.StatusCode == t.Expected {
			fmt.Printf("✅ %s : PASSED (Status %d)\n", t.Name, resp.StatusCode)
			passes++
		} else {
			fmt.Printf("❌ %s : FAILED (Expected %d, got %d)\n", t.Name, t.Expected, resp.StatusCode)
		}
		resp.Body.Close()
	}

	fmt.Println("==================================================")
	if passes == totalPasses {
		fmt.Println("🚀 ALL 7 PASSES SUCCESSFUL. Gateway is strictly validated.")
	} else {
		fmt.Printf("⚠️ WARNING: %d/%d Passes Succeeded.\n", passes, totalPasses)
	}
	fmt.Println("==================================================")
}
