package telemetry

import (
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func fixtureFirebaseToken(t *testing.T, mutate func(*firebaseJWTClaims)) string {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	firebaseKeysMu.Lock()
	oldKeys, oldExpiry := firebaseKeys, firebaseKeysExpire
	firebaseKeys = map[string]*rsa.PublicKey{"fixture-key": &key.PublicKey}
	firebaseKeysExpire = time.Now().Add(time.Hour)
	firebaseKeysMu.Unlock()
	t.Cleanup(func() {
		firebaseKeysMu.Lock()
		firebaseKeys = oldKeys
		firebaseKeysExpire = oldExpiry
		firebaseKeysMu.Unlock()
	})
	t.Setenv("AI_BS_ADMIN_EMAILS", "fixture-owner@local.invalid")
	claims := firebaseJWTClaims{Audience: firebaseProjectID, Issuer: "https://securetoken.google.com/" + firebaseProjectID, Subject: "fixture-user-A", Email: "fixture-owner@local.invalid", EmailVerified: true, IssuedAt: time.Now().Add(-time.Minute).Unix(), ExpiresAt: time.Now().Add(time.Hour).Unix()}
	if mutate != nil {
		mutate(&claims)
	}
	header, _ := json.Marshal(firebaseJWTHeader{Algorithm: "RS256", KeyID: "fixture-key"})
	body, _ := json.Marshal(claims)
	unsigned := base64.RawURLEncoding.EncodeToString(header) + "." + base64.RawURLEncoding.EncodeToString(body)
	digest := sha256.Sum256([]byte(unsigned))
	signature, err := rsa.SignPKCS1v15(rand.Reader, key, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatal(err)
	}
	return unsigned + "." + base64.RawURLEncoding.EncodeToString(signature)
}
func TestFirebaseIdentityReachesUpstreamWithoutMasterKey(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-local-admin-secret")
	token := fixtureFirebaseToken(t, nil)
	called := false
	handler := ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		if r.Header.Get("Authorization") != "Bearer "+token {
			t.Error("Firebase token changed")
		}
		if r.Header.Get("X-Admin-Key") != "" {
			t.Error("Firebase subject upgraded to shared local_admin")
		}
		w.WriteHeader(200)
	}))
	r := httptest.NewRequest("GET", "http://gateway/api/memory/conversations/identity", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, r)
	if w.Code != 200 || !called {
		t.Fatalf("verified Firebase blocked: %d", w.Code)
	}
}
func TestFirebaseNativeAuthorizationDoesNotRequireSharedMasterSecret(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "")
	token := fixtureFirebaseToken(t, nil)
	called := false
	handler := ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true; w.WriteHeader(200) }))
	r := httptest.NewRequest("GET", "http://gateway/api/daemons/status", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, r)
	if w.Code != 200 || !called {
		t.Fatalf("verified native route needed an unrelated key: %d", w.Code)
	}
}
func TestAnonymousSensitiveRoutesStopBeforeUpstream(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-local-admin-secret")
	for _, path := range []string{"/api/memory/conversations", "/api/coding/tasks", "/api/chat", "/api/v1/hybrid-chat/stream", "/api/daemons/status", "/api/tools/execute", "/api/executive/run"} {
		t.Run(path, func(t *testing.T) {
			called := false
			w := httptest.NewRecorder()
			ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true })).ServeHTTP(w, httptest.NewRequest("POST", "http://gateway"+path, nil))
			if w.Code != http.StatusUnauthorized || called {
				t.Fatalf("anonymous sensitive request reached handler: %d", w.Code)
			}
		})
	}
}
func TestInvalidKeyCannotReachPrivateHandler(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-local-admin-secret")
	called := false
	r := httptest.NewRequest("GET", "http://gateway/api/memory/conversations", nil)
	r.Header.Set("X-Admin-Key", "wrong")
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true })).ServeHTTP(w, r)
	if w.Code != 401 || called {
		t.Fatal("invalid key admitted")
	}
}
func TestExplicitLocalKeyIsPreserved(t *testing.T) {
	key := "fixture-local-admin-secret"
	t.Setenv("AI_BS_ADMIN_KEY", key)
	called := false
	r := httptest.NewRequest("GET", "http://gateway/api/memory/conversations", nil)
	r.Header.Set("X-Admin-Key", key)
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		if r.Header.Get("X-Admin-Key") != key {
			t.Error("explicit operator credential changed")
		}
		w.WriteHeader(200)
	})).ServeHTTP(w, r)
	if w.Code != 200 || !called {
		t.Fatal("valid key rejected")
	}
}
func TestMalformedBearerCannotReachPrivateHandler(t *testing.T) {
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-local-admin-secret")
	called := false
	r := httptest.NewRequest("GET", "http://gateway/api/memory/conversations", nil)
	r.Header.Set("Authorization", "Bearer not-a-jwt")
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true })).ServeHTTP(w, r)
	if w.Code != 401 || called {
		t.Fatal("malformed token admitted")
	}
}
func TestInvalidSignedFirebaseClaimsAreDenied(t *testing.T) {
	for name, mutate := range map[string]func(*firebaseJWTClaims){"expired": func(c *firebaseJWTClaims) { c.ExpiresAt = time.Now().Add(-time.Minute).Unix() }, "wrong-audience": func(c *firebaseJWTClaims) { c.Audience = "another-project" }, "unverified": func(c *firebaseJWTClaims) { c.EmailVerified = false }, "unlisted": func(c *firebaseJWTClaims) { c.Email = "other@local.invalid" }} {
		t.Run(name, func(t *testing.T) {
			t.Setenv("AI_BS_ADMIN_KEY", "fixture-local-admin-secret")
			token := fixtureFirebaseToken(t, mutate)
			called := false
			r := httptest.NewRequest("GET", "http://gateway/api/memory/conversations", nil)
			r.Header.Set("Authorization", "Bearer "+token)
			w := httptest.NewRecorder()
			ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true })).ServeHTTP(w, r)
			if w.Code != 401 || called {
				t.Fatal("invalid signed claims admitted")
			}
		})
	}
}
func TestUntrustedOriginCannotKeepReflectedCORS(t *testing.T) {
	r := httptest.NewRequest("GET", "http://gateway/health", nil)
	r.Header.Set("Origin", "https://untrusted.invalid")
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", r.Header.Get("Origin"))
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.WriteHeader(200)
	})).ServeHTTP(w, r)
	if w.Header().Get("Access-Control-Allow-Origin") != "" || w.Header().Get("Access-Control-Allow-Credentials") != "" {
		t.Fatal("upstream reflected untrusted origin survived gateway shield")
	}
}
func TestAllowedOriginAndExistingVaryArePreserved(t *testing.T) {
	r := httptest.NewRequest("GET", "http://gateway/health", nil)
	origin := "https://ai-bs-dashboard.web.app"
	r.Header.Set("Origin", origin)
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Vary", "Accept-Encoding")
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.WriteHeader(200)
	})).ServeHTTP(w, r)
	vary := strings.Join(w.Header().Values("Vary"), ",")
	if w.Header().Get("Access-Control-Allow-Origin") != origin || !strings.Contains(vary, "Accept-Encoding") || !strings.Contains(vary, "Origin") {
		t.Fatal("allowed origin or prior cache variation lost")
	}
}
func TestUntrustedPreflightDoesNotReachHandler(t *testing.T) {
	r := httptest.NewRequest("OPTIONS", "http://gateway/api/memory/conversations", nil)
	r.Header.Set("Origin", "https://untrusted.invalid")
	called := false
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true })).ServeHTTP(w, r)
	if w.Code != 403 || called {
		t.Fatal("untrusted preflight admitted")
	}
}
func TestResponseControllerFlushSurvivesShield(t *testing.T) {
	w := httptest.NewRecorder()
	ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := http.NewResponseController(w).Flush(); err != nil {
			t.Error(err)
		}
	})).ServeHTTP(w, httptest.NewRequest("GET", "http://gateway/health", nil))
	if !w.Flushed {
		t.Fatal("stream flushing lost")
	}
}
