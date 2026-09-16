package ipc

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// MLPayload represents a standard request sent from Go to the Python ML nodes.
type MLPayload struct {
	TaskType string                 `json:"task_type"` // e.g., "comfyui_generate", "ollama_chat"
	Params   map[string]interface{} `json:"params"`
}

// IPCBridge handles high-speed communication between Go (Gateway) and Python (ML Worker)
type IPCBridge struct {
	PythonPort string
	client     *http.Client
}

// NewIPCBridge initializes a fast localhost connection.
func NewIPCBridge(port string) *IPCBridge {
	return &IPCBridge{
		PythonPort: port,
		// Using a highly optimized HTTP client tailored for local IPC
		client: &http.Client{
			Timeout: 120 * time.Second, // ML tasks can take time (e.g. image generation)
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 100,
				IdleConnTimeout:     90 * time.Second,
			},
		},
	}
}

// Dispatch forwards an ML task to the Python GPU worker node.
func (ipc *IPCBridge) Dispatch(payload MLPayload) ([]byte, error) {
	url := fmt.Sprintf("http://127.0.0.1:%s/internal/ml-task", ipc.PythonPort)

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to encode ML payload: %w", err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	
	// Add internal security header so Python knows it came from the local Go Gateway
	req.Header.Set("X-AIBS-Internal-Auth", "trusted_go_core")

	resp, err := ipc.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("Python ML worker unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Python ML worker returned status: %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}
