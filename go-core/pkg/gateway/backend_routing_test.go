package gateway

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func TestConfiguredBackendOwnsProductionProxyRoutes(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-routing-key")
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer fixture-routing-key" {
			t.Error("Original credential changed")
		}
		w.Header().Set("Cache-Control", "private, no-store")
		w.WriteHeader(206)
		io.WriteString(w, r.URL.RequestURI())
	}))
	defer upstream.Close()
	target, _ := url.Parse(upstream.URL)
	gateway := NewGateway("0", target.Port(), nil)
	for _, path := range []string{"/api/v1/fe-express/driver-records/identity", "/api/personal-finance/payments?week_start=2026-11-09", "/v1/fixture", "/api/comfy/media?filename=fixture.png"} {
		request := httptest.NewRequest("GET", path, nil)
		request.Header.Set("Authorization", "Bearer fixture-routing-key")
		request.Header.Set("Origin", "https://ai-bs-dashboard.web.app")
		response := httptest.NewRecorder()
		gateway.Handler().ServeHTTP(response, request)
		if response.Code != 206 || response.Body.String() != path {
			t.Fatalf("Configured upstream did not receive %s: %d %s", path, response.Code, response.Body.String())
		}
		if response.Header().Get("Access-Control-Allow-Origin") != "https://ai-bs-dashboard.web.app" || response.Header().Get("Cache-Control") != "private, no-store" {
			t.Fatal("Gateway changed CORS/private response boundary")
		}
	}
}

func TestInvalidBackendPortFailsBeforeForwarding(t *testing.T) {
	for _, port := range []string{"", "0", "-1", "65536", "8080/path", "8080@external.invalid", " 8080"} {
		gateway := NewGateway("0", port, nil)
		response := httptest.NewRecorder()
		gateway.Handler().ServeHTTP(response, httptest.NewRequest("GET", "/api/personal-finance/payments", nil))
		if response.Code != 500 {
			t.Fatalf("Invalid port %q did not fail closed: %d", port, response.Code)
		}
	}
	gateway := NewGateway("0", "8080", nil)
	gateway.IPCBridge = nil
	response := httptest.NewRecorder()
	gateway.Handler().ServeHTTP(response, httptest.NewRequest("GET", "/api/personal-finance/payments", nil))
	if response.Code != 500 {
		t.Fatal("Missing bridge silently fell back")
	}
}

func TestDefaultBackendAndHealthRemainSeparate(t *testing.T) {
	gateway := NewGateway("0", "8080", nil)
	gateway.Version = "fixture-version"
	target, err := gateway.pythonBackendURL()
	if err != nil || target.String() != "http://127.0.0.1:8080" {
		t.Fatal("Default backend contract changed")
	}
	gateway.IPCBridge = nil
	response := httptest.NewRecorder()
	gateway.Handler().ServeHTTP(response, httptest.NewRequest("GET", "/api/health", nil))
	if response.Code != 200 || !strings.Contains(response.Body.String(), "fixture-version") {
		t.Fatal("Direct health route incorrectly depends on Python")
	}
}
