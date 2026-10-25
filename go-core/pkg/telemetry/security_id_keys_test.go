package telemetry

import (
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"io"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

type idTokenKeyTransport func(*http.Request) (*http.Response, error)

func (f idTokenKeyTransport) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

// A cold verifier must fetch ID-token keys. Preseeding the cache would hide a
// session-cookie certificate endpoint accidentally used for browser ID tokens.
func TestColdFirebaseIDTokenFetchesCorrectCertificatesAndCaches(t *testing.T) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	now := time.Now()
	cert := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "fixture-only"}, NotBefore: now.Add(-time.Hour), NotAfter: now.Add(time.Hour)}
	der, err := x509.CreateCertificate(rand.Reader, cert, cert, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	certificates, _ := json.Marshal(map[string]string{"cold-fixture-key": string(pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}))})
	oldTransport := http.DefaultTransport
	firebaseKeysMu.Lock()
	oldKeys, oldExpiry := firebaseKeys, firebaseKeysExpire
	firebaseKeys, firebaseKeysExpire = nil, time.Time{}
	firebaseKeysMu.Unlock()
	t.Cleanup(func() {
		http.DefaultTransport = oldTransport
		firebaseKeysMu.Lock()
		firebaseKeys, firebaseKeysExpire = oldKeys, oldExpiry
		firebaseKeysMu.Unlock()
	})
	requests := 0
	http.DefaultTransport = idTokenKeyTransport(func(r *http.Request) (*http.Response, error) {
		requests++
		if r.URL.String() != "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com" {
			t.Errorf("browser ID token requested the wrong certificate endpoint: %s", r.URL.String())
			return &http.Response{StatusCode: 404, Header: make(http.Header), Body: io.NopCloser(strings.NewReader("wrong key family"))}, nil
		}
		return &http.Response{StatusCode: 200, Header: http.Header{"Cache-Control": {"public, max-age=7200"}}, Body: io.NopCloser(strings.NewReader(string(certificates)))}, nil
	})
	t.Setenv("AI_BS_ADMIN_EMAILS", "cold-owner@local.invalid")
	t.Setenv("AI_BS_ADMIN_KEY", "fixture-unrelated-local-key")
	header, _ := json.Marshal(firebaseJWTHeader{Algorithm: "RS256", KeyID: "cold-fixture-key"})
	claims, _ := json.Marshal(firebaseJWTClaims{Audience: firebaseProjectID, Issuer: "https://securetoken.google.com/" + firebaseProjectID, Subject: "cold-fixture-owner", Email: "cold-owner@local.invalid", EmailVerified: true, IssuedAt: now.Add(-time.Minute).Unix(), ExpiresAt: now.Add(time.Hour).Unix()})
	unsigned := base64.RawURLEncoding.EncodeToString(header) + "." + base64.RawURLEncoding.EncodeToString(claims)
	digest := sha256.Sum256([]byte(unsigned))
	signature, err := rsa.SignPKCS1v15(rand.Reader, key, crypto.SHA256, digest[:])
	if err != nil {
		t.Fatal(err)
	}
	token := unsigned + "." + base64.RawURLEncoding.EncodeToString(signature)
	for i := 0; i < 2; i++ {
		called := false
		r := httptest.NewRequest("GET", "http://gateway/api/memory/conversations/identity", nil)
		r.Header.Set("Authorization", "Bearer "+token)
		w := httptest.NewRecorder()
		ActiveDefenseShield(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			called = true
			if r.Header.Get("Authorization") != "Bearer "+token || r.Header.Get("X-Admin-Key") != "" {
				t.Error("subject credential was changed or upgraded")
			}
			w.WriteHeader(http.StatusNoContent)
		})).ServeHTTP(w, r)
		if w.Code != http.StatusNoContent || !called {
			t.Fatalf("cold/cached ID token rejected: %d", w.Code)
		}
	}
	if requests != 1 {
		t.Fatalf("expected one cached certificate fetch, got %d", requests)
	}
	if time.Until(firebaseKeysExpire) < 119*time.Minute {
		t.Error("certificate max-age not respected")
	}
	if isFirebaseAdminToken(unsigned + "." + base64.RawURLEncoding.EncodeToString(make([]byte, 256))) {
		t.Error("forged signature accepted")
	}
}
