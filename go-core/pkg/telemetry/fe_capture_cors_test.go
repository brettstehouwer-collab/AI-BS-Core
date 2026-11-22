package telemetry

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestFECapturePreflight(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-cors-admin-key")
	for _, scenario := range []struct {
		name, origin string
		status       int
	}{
		{"hosted", "https://ai-bs-dashboard.web.app", 204},
		{"desktop", "http://localhost:5173", 204},
		{"foreign", "https://untrusted.invalid", 403},
		{"lookalike", "https://ai-bs-dashboard.web.app.untrusted.invalid", 403},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			called := false
			handler := ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }))
			request := httptest.NewRequest("OPTIONS", "/api/v1/fe-express/driver-records/loads/fixture/attachments", nil)
			request.Header.Set("Origin", scenario.origin)
			request.Header.Set("Access-Control-Request-Method", "POST")
			request.Header.Set("Access-Control-Request-Headers", "authorization,content-type,x-operation-id")
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			if response.Code != scenario.status || called {
				t.Fatalf("preflight changed admission: status=%d called=%v", response.Code, called)
			}
			if scenario.status == 204 {
				if response.Header().Get("Access-Control-Allow-Origin") != scenario.origin ||
					!strings.Contains(strings.ToLower(response.Header().Get("Access-Control-Allow-Headers")), "x-operation-id") {
					t.Fatal("capture operation header or exact trusted origin missing")
				}
			} else if response.Header().Get("Access-Control-Allow-Origin") != "" {
				t.Fatal("foreign origin admitted")
			}
		})
	}
	for _, authorized := range []bool{false, true} {
		name := "anonymous_remains_denied"
		if authorized {
			name = "configured_credential_and_operation_preserved"
		}
		t.Run(name, func(t *testing.T) {
			called := false
			handler := ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				called = true
				if r.Header.Get("X-Operation-Id") != "fixture-operation" || r.Header.Get("X-Admin-Key") != "fixture-cors-admin-key" {
					t.Error("credential or operation identity changed")
				}
				w.WriteHeader(http.StatusAccepted)
			}))
			request := httptest.NewRequest("POST", "/api/chat", nil)
			request.Header.Set("Origin", "https://ai-bs-dashboard.web.app")
			request.Header.Set("X-Operation-Id", "fixture-operation")
			if authorized {
				request.Header.Set("X-Admin-Key", "fixture-cors-admin-key")
			}
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			if authorized && (response.Code != 202 || !called) {
				t.Fatal("configured credential was not forwarded")
			}
			if !authorized && (response.Code != 401 || called) {
				t.Fatal("CORS change bypassed authentication")
			}
		})
	}
}
