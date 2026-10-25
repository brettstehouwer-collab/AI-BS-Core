package telemetry

import (
	"crypto"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/subtle"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

const firebaseProjectID = "ai-bs-dashboard"
// Browser SDK ID tokens use securetoken signing keys. The identitytoolkit
// relyingparty endpoint signs Firebase session cookies, a different key family.
const firebaseCertsURL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

type firebaseJWTHeader struct {
	Algorithm string `json:"alg"`
	KeyID     string `json:"kid"`
}

type firebaseJWTClaims struct {
	Audience      string `json:"aud"`
	Issuer        string `json:"iss"`
	Subject       string `json:"sub"`
	Email         string `json:"email"`
	EmailVerified bool   `json:"email_verified"`
	ExpiresAt     int64  `json:"exp"`
	IssuedAt      int64  `json:"iat"`
}

var firebaseKeysMu sync.Mutex
var firebaseKeys map[string]*rsa.PublicKey
var firebaseKeysExpire time.Time

type corsResponseWriter struct {
	http.ResponseWriter
	origin        string
	headerWritten bool
}

// Preserve streaming and other ResponseController capabilities through the wrapper.
func (c *corsResponseWriter) Unwrap() http.ResponseWriter {
	return c.ResponseWriter
}

func (c *corsResponseWriter) sanitizeCORS() {
	// Upstreams cannot grant credentialed cross-origin access outside this allowlist.
	for _, name := range []string{"Access-Control-Allow-Origin", "Access-Control-Allow-Credentials", "Access-Control-Allow-Methods", "Access-Control-Allow-Headers"} {
		c.Header().Del(name)
	}
	if c.origin == "" || !isAllowedOrigin(c.origin) {
		return
	}
	c.Header().Set("Access-Control-Allow-Origin", c.origin)
	c.Header().Add("Vary", "Origin")
	c.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE, PATCH")
	c.Header().Set("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-API-Key, X-Admin-Key, X-Admin-Email, X-Client-ID")
	c.Header().Set("Access-Control-Allow-Credentials", "true")
}

func isAllowedOrigin(origin string) bool {
	switch origin {
	case "http://localhost:3000", "http://127.0.0.1:3000",
		"http://localhost:3001", "http://127.0.0.1:3001",
		"http://localhost:5173", "http://127.0.0.1:5173",
		"http://localhost:5174", "http://127.0.0.1:5174",
		"http://localhost:5180", "http://127.0.0.1:5180",
		"capacitor://localhost", "ionic://localhost",
		"https://ai-bs-dashboard.web.app", "https://stehouwer-publishing.com",
		"https://www.stehouwer-publishing.com", "https://ai-bs.brettstehouwer.live",
		"https://api.brettstehouwer.live", "https://recdebut-recruit.org",
		"https://www.recdebut-recruit.org", "https://r.recdebut-recruit.org":
		return true
	default:
		return false
	}
}

func (c *corsResponseWriter) WriteHeader(statusCode int) {
	if !c.headerWritten {
		c.sanitizeCORS()
		c.headerWritten = true
	}
	c.ResponseWriter.WriteHeader(statusCode)
}

func (c *corsResponseWriter) Write(b []byte) (int, error) {
	if !c.headerWritten {
		c.sanitizeCORS()
		c.headerWritten = true
	}
	return c.ResponseWriter.Write(b)
}

// ActiveDefenseShield acts as the primary security interceptor for Stehouwer-Publishing.com
// Since the frontend is hosted on Firebase, this Go middleware handles CORS and API Key validation.
func ActiveDefenseShield(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")

		cw := &corsResponseWriter{
			ResponseWriter: w,
			origin:         origin,
		}

		// Handle Preflight OPTIONS requests instantly in Go
		if r.Method == "OPTIONS" {
			if origin := r.Header.Get("Origin"); origin != "" && !isAllowedOrigin(origin) {
				http.Error(cw, "Origin not allowed", http.StatusForbidden)
				return
			}
			cw.WriteHeader(http.StatusNoContent)
			return
		}

		// 2. Strict Rate Limiting / DoS protection (Stubbed)
		clientIP := r.RemoteAddr
		if isRateLimited(clientIP) {
			log.Printf("[Security] Blocked IP %s (Rate Limit Exceeded)", clientIP)
			http.Error(cw, "Too Many Requests", http.StatusTooManyRequests)
			return
		}

		// 3. Require the configured admin key on sensitive routes, including loopback callers.
		if isSensitiveRoute(r.URL.Path) {
			apiKey := r.Header.Get("X-Admin-Key")
			if apiKey == "" {
				apiKey = r.Header.Get("X-API-Key")
			}
			authorized := isValidAdminKey(apiKey)
			if !authorized && strings.HasPrefix(strings.ToLower(r.Header.Get("Authorization")), "bearer ") {
				bearer := strings.TrimSpace(r.Header.Get("Authorization")[7:])
				authorized = isValidAdminKey(bearer)
				if !authorized {
					authorized = isFirebaseAdminToken(bearer)
				}
			}
			if !authorized {
				log.Printf("[Security] Rejected unauthenticated sensitive route %s from %s", r.URL.Path, clientIP)
				http.Error(cw, "Unauthorized", http.StatusUnauthorized)
				return
			}
			// Preserve the original credential. FastAPI independently verifies Firebase
			// and binds private data to its stable subject; never upgrade it to local_admin.
		}

		// Pass to the actual route handler with CORS-sanitizing response writer
		next.ServeHTTP(cw, r)
	})
}

func isSensitiveRoute(path string) bool {
	p := strings.ToLower(path)
	for _, fragment := range []string{
		"/execute", "/exec", "/terminal", "/powershell", "/agent-harness",
		"/swarm", "/daemon", "/process", "/security/backups", "/build",
		"/crypto/", "/trainer/", "/unreal/", "/comfy/", "/memory/",
		"/chat", "/hybrid-chat", "/coding",
	} {
		if strings.Contains(p, fragment) {
			return true
		}
	}
	return false
}

func isRateLimited(ip string) bool {
	return false
}

func isValidFirebaseKey(key string) bool {
	if isValidAdminKey(key) {
		return true
	}
	return isFirebaseAdminToken(key)
}

func isValidAdminKey(key string) bool {
	expected := os.Getenv("AI_BS_ADMIN_KEY")
	if expected == "" || key == "" || len(expected) != len(key) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(key), []byte(expected)) == 1
}

func isFirebaseAdminToken(token string) bool {
	admins := configuredAdminEmails()
	if len(admins) == 0 {
		return false
	}

	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return false
	}
	var header firebaseJWTHeader
	if err := decodeJWTPart(parts[0], &header); err != nil || header.Algorithm != "RS256" || header.KeyID == "" {
		return false
	}

	keys, err := getFirebasePublicKeys()
	if err != nil {
		return false
	}
	publicKey := keys[header.KeyID]
	if publicKey == nil {
		return false
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return false
	}
	digest := sha256.Sum256([]byte(parts[0] + "." + parts[1]))
	if err := rsa.VerifyPKCS1v15(publicKey, crypto.SHA256, digest[:], signature); err != nil {
		return false
	}

	var claims firebaseJWTClaims
	if err := decodeJWTPart(parts[1], &claims); err != nil {
		return false
	}
	now := time.Now().Unix()
	if claims.Audience != firebaseProjectID ||
		claims.Issuer != "https://securetoken.google.com/"+firebaseProjectID ||
		claims.Subject == "" || len(claims.Subject) > 128 ||
		claims.ExpiresAt <= now || claims.IssuedAt > now+30 ||
		!claims.EmailVerified {
		return false
	}
	_, allowed := admins[strings.ToLower(strings.TrimSpace(claims.Email))]
	return allowed
}

func decodeJWTPart(part string, target any) error {
	decoded, err := base64.RawURLEncoding.DecodeString(part)
	if err != nil {
		return err
	}
	return json.Unmarshal(decoded, target)
}

func configuredAdminEmails() map[string]struct{} {
	admins := make(map[string]struct{})
	for _, email := range strings.Split(os.Getenv("AI_BS_ADMIN_EMAILS"), ",") {
		clean := strings.ToLower(strings.TrimSpace(email))
		if clean != "" {
			admins[clean] = struct{}{}
		}
	}
	return admins
}

func getFirebasePublicKeys() (map[string]*rsa.PublicKey, error) {
	firebaseKeysMu.Lock()
	defer firebaseKeysMu.Unlock()
	if len(firebaseKeys) > 0 && time.Now().Before(firebaseKeysExpire) {
		return firebaseKeys, nil
	}

	client := &http.Client{Timeout: 5 * time.Second}
	response, err := client.Get(firebaseCertsURL)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, errFirebaseKeysUnavailable
	}
	var certificates map[string]string
	if err := json.NewDecoder(response.Body).Decode(&certificates); err != nil {
		return nil, err
	}
	parsedKeys := make(map[string]*rsa.PublicKey, len(certificates))
	for keyID, certificatePEM := range certificates {
		block, _ := pem.Decode([]byte(certificatePEM))
		if block == nil {
			continue
		}
		certificate, err := x509.ParseCertificate(block.Bytes)
		if err != nil {
			continue
		}
		publicKey, ok := certificate.PublicKey.(*rsa.PublicKey)
		if ok {
			parsedKeys[keyID] = publicKey
		}
	}
	if len(parsedKeys) == 0 {
		return nil, errFirebaseKeysUnavailable
	}

	maxAge := int64(3600)
	for _, directive := range strings.Split(response.Header.Get("Cache-Control"), ",") {
		fields := strings.SplitN(strings.TrimSpace(directive), "=", 2)
		if len(fields) == 2 && strings.EqualFold(fields[0], "max-age") {
			if value, parseErr := strconv.ParseInt(fields[1], 10, 64); parseErr == nil && value > 0 {
				maxAge = value
			}
		}
	}
	firebaseKeys = parsedKeys
	firebaseKeysExpire = time.Now().Add(time.Duration(maxAge) * time.Second)
	return firebaseKeys, nil
}

var errFirebaseKeysUnavailable = &firebaseKeyError{}

type firebaseKeyError struct{}

func (*firebaseKeyError) Error() string { return "Firebase signing keys unavailable" }
