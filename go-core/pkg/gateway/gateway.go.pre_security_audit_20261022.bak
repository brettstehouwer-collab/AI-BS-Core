package gateway

import (
	"encoding/json"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"aibs_core/pkg/ipc"
	"aibs_core/pkg/telemetry"
	"aibs_core/pkg/supervisor"
)

// Gateway represents the primary HTTP interface for AI-BS.
type Gateway struct {
	Port       string
	IPCBridge  *ipc.IPCBridge
	Supervisor *supervisor.Supervisor
}

// NewGateway creates a new instance of the Commercial Gateway.
func NewGateway(port string, pythonPort string, s *supervisor.Supervisor) *Gateway {
	return &Gateway{
		Port:       port,
		IPCBridge:  ipc.NewIPCBridge(pythonPort),
		Supervisor: s,
	}
}

// Start Server initializes the HTTP routes and listens for incoming traffic.
func (g *Gateway) StartServer() {
	mux := http.NewServeMux()

	// Direct Go Routes (Instantly handled, no Python needed)
	mux.HandleFunc("/api/health", g.healthHandler)
	mux.HandleFunc("/health", g.healthHandler)
	mux.HandleFunc("/v1/health", g.healthHandler)
	mux.HandleFunc("/api/models", g.modelsHandler)
	mux.HandleFunc("/models", g.modelsHandler)
	mux.HandleFunc("/v1/models", g.modelsHandler)
	
	// Daemon Routes
	mux.HandleFunc("/api/daemons/status", g.daemonStatusHandler)
	mux.HandleFunc("/api/daemons/", g.daemonControlHandler)

	// Proxy Route (Delegated to Python ML Worker)
	mux.HandleFunc("/api/comfy/media", g.proxyComfyMediaHandler)

	// Catch-all Proxy for Analytics, Admin, etc to Python FastApi on 8080
	mux.HandleFunc("/api/", g.proxyToPythonBackend)
	mux.HandleFunc("/v1/", g.proxyToPythonBackend)

	// Wrap the entire multiplexer in the Active Defense Shield
	securedMux := telemetry.ActiveDefenseShield(mux)

	log.Printf("[Gateway] Commercial Gateway listening on 0.0.0.0:%s", g.Port)
	if err := http.ListenAndServe("0.0.0.0:"+g.Port, securedMux); err != nil {
		log.Fatalf("[Gateway] Server failed: %v", err)
	}
}

// healthHandler replaces the Python /api/health endpoint
func (g *Gateway) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	response := map[string]interface{}{
		"status":          "online",
		"service":         "AI-BS Central Cognitive Engine API (Go Gateway)",
		"gpu_accelerated": true,
		"timestamp":       time.Now().Unix(),
	}
	json.NewEncoder(w).Encode(response)
}

// modelsHandler replaces the Python /api/models endpoint
func (g *Gateway) modelsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	models := []string{"stehouwer_llm", "stehouwer_qwen", "stehouwer_hermes", "stehouwer_dolphin"}
	resp, err := http.Get("http://127.0.0.1:11434/api/tags")
	if err == nil && resp.StatusCode == 200 {
		var tagData struct {
			Models []struct {
				Name string `json:"name"`
			} `json:"models"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&tagData); err == nil {
			ollamaList := []string{"stehouwer_llm"}
			for _, m := range tagData.Models {
				cleanName := m.Name
				if idx := strings.Index(cleanName, ":"); idx != -1 {
					cleanName = cleanName[:idx]
				}
				exists := false
				for _, existing := range ollamaList {
					if existing == cleanName {
						exists = true
						break
					}
				}
				if !exists && cleanName != "" {
					ollamaList = append(ollamaList, cleanName)
				}
			}
			if len(ollamaList) > 1 {
				models = ollamaList
			}
		}
		resp.Body.Close()
	}
	response := map[string]interface{}{
		"status": "success",
		"models": models,
	}
	json.NewEncoder(w).Encode(response)
}

// proxyComfyMediaHandler delegates to Python/ComfyUI backend on port 8080
func (g *Gateway) proxyComfyMediaHandler(w http.ResponseWriter, r *http.Request) {
	targetURL, err := url.Parse("http://127.0.0.1:8080")
	if err != nil {
		http.Error(w, "Failed to parse target URL", http.StatusInternalServerError)
		return
	}
	
	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	r.Host = targetURL.Host
	proxy.ModifyResponse = func(resp *http.Response) error {
		if origin := r.Header.Get("Origin"); origin != "" {
			resp.Header.Set("Access-Control-Allow-Origin", origin)
		} else {
			resp.Header.Set("Access-Control-Allow-Origin", "*")
		}
		resp.Header.Set("Access-Control-Allow-Credentials", "true")
		return nil
	}
	proxy.ServeHTTP(w, r)
}

// daemonStatusHandler returns the live state of all managed daemons.
func (g *Gateway) daemonStatusHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	
	status := g.Supervisor.GetStatus()
	json.NewEncoder(w).Encode(status)
}

// daemonControlHandler parses /api/daemons/{name}/{action}
func (g *Gateway) daemonControlHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	
	// Expecting /api/daemons/name/start or /api/daemons/name/stop
	path := strings.TrimPrefix(r.URL.Path, "/api/daemons/")
	parts := strings.Split(path, "/")
	if len(parts) != 2 {
		http.Error(w, "Invalid daemon route", http.StatusBadRequest)
		return
	}
	
	name, action := parts[0], parts[1]
	
	var err error
	switch action {
	case "start":
		err = g.Supervisor.StartDaemon(name)
	case "stop":
		err = g.Supervisor.StopDaemon(name)
	default:
		http.Error(w, "Invalid action, must be start or stop", http.StatusBadRequest)
		return
	}
	
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"status": "error", "message": err.Error()})
		return
	}
	
	json.NewEncoder(w).Encode(map[string]string{"status": "success", "message": "Action " + action + " executed for " + name})
}

// proxyToPythonBackend forwards unknown /api/ requests to the Python FastAPI server on 8080
func (g *Gateway) proxyToPythonBackend(w http.ResponseWriter, r *http.Request) {
	targetURL, err := url.Parse("http://127.0.0.1:8080")
	if err != nil {
		http.Error(w, "Failed to parse target URL", http.StatusInternalServerError)
		return
	}
	
	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.FlushInterval = -1
	// Update the headers to allow for proper routing and deduplicate CORS headers
	r.Host = targetURL.Host
	proxy.ModifyResponse = func(resp *http.Response) error {
		if origin := r.Header.Get("Origin"); origin != "" {
			resp.Header.Set("Access-Control-Allow-Origin", origin)
		} else {
			resp.Header.Set("Access-Control-Allow-Origin", "*")
		}
		resp.Header.Set("Access-Control-Allow-Credentials", "true")
		return nil
	}
	proxy.ServeHTTP(w, r)
}
