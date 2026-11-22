package telemetry

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestPersonalFinanceDocumentCORS(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-personal-cors")
	for _, origin := range []string{"https://ai-bs-dashboard.web.app", "https://untrusted.invalid"} {
		called := false
		handler := ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }))
		request := httptest.NewRequest("OPTIONS", "/api/personal-finance/payments/1/documents", nil)
		request.Header.Set("Origin", origin)
		request.Header.Set("Access-Control-Request-Method", "POST")
		request.Header.Set("Access-Control-Request-Headers", "authorization,idempotency-key,x-document-name,x-document-name-encoding,content-type")
		response := httptest.NewRecorder()
		handler.ServeHTTP(response, request)
		if called {
			t.Fatal("Preflight reached an application handler")
		}
		if origin == "https://untrusted.invalid" {
			if response.Code != 403 || response.Header().Get("Access-Control-Allow-Origin") != "" {
				t.Fatal("Foreign origin admitted")
			}
			continue
		}
		if response.Code != 204 || response.Header().Get("Access-Control-Allow-Origin") != origin {
			t.Fatal("Trusted preflight failed")
		}
		for _, name := range []string{"idempotency-key", "x-document-name", "x-document-name-encoding"} {
			if !strings.Contains(strings.ToLower(response.Header().Get("Access-Control-Allow-Headers")), name) {
				t.Fatal("Missing personal document header", name)
			}
		}
	}
	for _, authenticated := range []bool{false, true} {
		called := false
		handler := ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			called = true
			want := ""
			if authenticated {
				want = "fixture-personal-cors"
			}
			if r.Header.Get("X-Admin-Key") != want {
				t.Fatal("Gateway changed original credentials")
			}
			w.WriteHeader(202)
		}))
		request := httptest.NewRequest("POST", "/api/personal-finance/payments/1/documents", nil)
		request.Header.Set("Origin", "https://ai-bs-dashboard.web.app")
		if authenticated {
			request.Header.Set("X-Admin-Key", "fixture-personal-cors")
		}
		response := httptest.NewRecorder()
		handler.ServeHTTP(response, request)
		// This route's financial-owner admission is in FastAPI, not the gateway's
		// legacy sensitive-fragment list. The gateway must preserve credentials.
		if !called || response.Code != 202 {
			t.Fatal("Personal route forwarding changed")
		}
	}
}
