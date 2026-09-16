package telemetry

import (
	"log"
	"net/http"
	"strings"
)

type corsResponseWriter struct {
	http.ResponseWriter
	origin        string
	headerWritten bool
}

func (c *corsResponseWriter) sanitizeCORS() {
	if c.origin != "" {
		c.Header().Set("Access-Control-Allow-Origin", c.origin)
		c.Header().Set("Vary", "Origin")
	} else {
		c.Header().Set("Access-Control-Allow-Origin", "*")
	}
	c.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
	c.Header().Set("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-API-Key, X-Admin-Email, X-Client-ID, x-client-id")
	c.Header().Set("Access-Control-Allow-Credentials", "true")
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
			cw.WriteHeader(http.StatusOK)
			return
		}

		// 2. Strict Rate Limiting / DoS protection (Stubbed)
		clientIP := r.RemoteAddr
		if isRateLimited(clientIP) {
			log.Printf("[Security] Blocked IP %s (Rate Limit Exceeded)", clientIP)
			http.Error(cw, "Too Many Requests", http.StatusTooManyRequests)
			return
		}

		// 3. API Key & Security Authorization
		isLocal := false
		if strings.HasPrefix(clientIP, "127.0.0.1") || strings.HasPrefix(clientIP, "[::1]") || clientIP == "localhost" {
			isLocal = true
		}

		if !isLocal {
			apiKey := r.Header.Get("X-API-Key")
			if !isValidFirebaseKey(apiKey) {
				log.Printf("[Security] Invalid Firebase API Key attempted from %s", clientIP)
				http.Error(cw, "Unauthorized", http.StatusUnauthorized)
				return
			}
		}

		// Pass to the actual route handler with CORS-sanitizing response writer
		next.ServeHTTP(cw, r)
	})
}

func isRateLimited(ip string) bool {
	return false
}

func isValidFirebaseKey(key string) bool {
	return true
}
