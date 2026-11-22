package daemons

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"cryptoswarm-desktop/internal/queue"
)

const sharedSecret = "matrix_execution_secret_77"
const cryptoComBaseURL = "https://api.crypto.com/v2"

func validateToken(intent map[string]interface{}, token string) bool {
	intentBytes, _ := json.Marshal(intent)
	hash := sha256.Sum256([]byte(fmt.Sprintf("%s:%s", intentBytes, sharedSecret)))
	return token == hex.EncodeToString(hash[:])
}

func sendDiscordWebhook(txID, pair, action string, notional, price, tp, sl float64) {
	url := os.Getenv("DISCORD_WEBHOOK_URL")
	if url == "" {
		return
	}

	color := 15548997 // Red (SELL)
	if strings.ToLower(action) == "buy" {
		color = 5763719 // Green (BUY)
	}

	mode := "🟢 LIVE"
	if strings.HasPrefix(txID, "sim_") {
		mode = "📄 PAPER"
	}

	embed := map[string]interface{}{
		"title":       fmt.Sprintf("🚨 VIP Trade Alert: %s %s", strings.ToUpper(action), pair),
		"description": fmt.Sprintf("Matrix Engine executed a %s **%s** order. Mode: %s", strings.ToLower(action), pair, mode),
		"color":       color,
		"fields": []map[string]interface{}{
			{"name": "Symbol", "value": fmt.Sprintf("**%s**", pair), "inline": true},
			{"name": "Action", "value": fmt.Sprintf("**%s**", strings.ToUpper(action)), "inline": true},
			{"name": "Mode", "value": mode, "inline": true},
			{"name": "Exec Price", "value": fmt.Sprintf("$%.8f", price), "inline": true},
			{"name": "Notional (USD)", "value": fmt.Sprintf("$%.4f", notional), "inline": true},
			{"name": "Take Profit", "value": fmt.Sprintf("$%.8f", tp), "inline": true},
			{"name": "Stop Loss", "value": fmt.Sprintf("$%.8f", sl), "inline": true},
		},
		"footer": map[string]interface{}{
			"text": fmt.Sprintf("TX ID: %s", txID),
		},
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}

	payload := map[string]interface{}{
		"username":   "Crypto Swarm VIP",
		"avatar_url": "https://i.imgur.com/R211wzY.png",
		"embeds":     []map[string]interface{}{embed},
	}

	body, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 5 * time.Second}
	if _, err := client.Do(req); err != nil {
		log.Printf("[Trade Engine] Discord webhook failed: %v\n", err)
	}
}

// CryptoComClient handles authenticated requests to the Crypto.com Exchange API v2.
type CryptoComClient struct {
	APIKey    string
	APISecret string
	reqID     int64
}

// buildParamString sorts params by key and concatenates key+value pairs.
func buildParamString(params map[string]interface{}) string {
	keys := make([]string, 0, len(params))
	for k := range params {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	var sb strings.Builder
	for _, k := range keys {
		sb.WriteString(k)
		sb.WriteString(fmt.Sprintf("%v", params[k]))
	}
	return sb.String()
}

// sign computes the HMAC-SHA256 signature for a Crypto.com API request.
func (c *CryptoComClient) sign(method string, id int64, params map[string]interface{}, nonce int64) string {
	paramStr := buildParamString(params)
	payload := method + strconv.FormatInt(id, 10) + c.APIKey + paramStr + strconv.FormatInt(nonce, 10)
	mac := hmac.New(sha256.New, []byte(c.APISecret))
	mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil))
}

// doRequest sends a signed POST to the Crypto.com private API.
func (c *CryptoComClient) doRequest(method string, params map[string]interface{}) (map[string]interface{}, error) {
	if strings.Contains(method, "create-order") {
		return nil, fmt.Errorf("live dispatch held: reconciliation required")
	}
	c.reqID++
	id := c.reqID
	nonce := time.Now().UnixMilli()

	sig := c.sign(method, id, params, nonce)

	reqBody := map[string]interface{}{
		"id":      id,
		"method":  method,
		"api_key": c.APIKey,
		"params":  params,
		"nonce":   nonce,
		"sig":     sig,
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/%s", cryptoComBaseURL, method)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 15 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	if code, ok := result["code"].(float64); ok && code != 0 {
		msg, _ := result["message"].(string)
		return nil, fmt.Errorf("API error code %.0f: %s", code, msg)
	}

	return result, nil
}

// GetBalance fetches the available balance for a given currency.
func (c *CryptoComClient) GetBalance(currency string) (float64, error) {
	result, err := c.doRequest("private/get-account-summary", map[string]interface{}{
		"currency": currency,
	})
	if err != nil {
		return 0, err
	}

	res, ok := result["result"].(map[string]interface{})
	if !ok {
		return 0, fmt.Errorf("missing result in balance response")
	}

	accounts, ok := res["accounts"].([]interface{})
	if !ok || len(accounts) == 0 {
		return 0, fmt.Errorf("no accounts found for currency %s", currency)
	}

	account, ok := accounts[0].(map[string]interface{})
	if !ok {
		return 0, fmt.Errorf("invalid account structure")
	}

	available, ok := account["available"].(float64)
	if !ok {
		return 0, fmt.Errorf("available balance field missing for %s", currency)
	}
	return available, nil
}

// CreateOrder places a MARKET order. allocationPct is 0-100.
func (c *CryptoComClient) CreateOrder(pair, action string, allocationPct float64) (string, float64, error) {
	if cryptoLiveDispatchBlocked() {
		return "", 0, fmt.Errorf("live dispatch held: fill and balance reconciliation required")
	}
	if c.APIKey == "" || c.APISecret == "" {
		return "", 0, fmt.Errorf("API keys not configured")
	}

	instrument := strings.ReplaceAll(pair, "/", "_")
	side := strings.ToUpper(action)

	var params map[string]interface{}
	var notional float64

	if side == "BUY" {
		usdBalance, err := c.GetBalance("USD")
		if err != nil {
			return "", 0, fmt.Errorf("get USD balance: %w", err)
		}
		notional = usdBalance * allocationPct / 100.0
		if notional < 1.0 {
			return "", 0, fmt.Errorf("notional $%.4f below $1.00 minimum (USD balance: $%.4f)", notional, usdBalance)
		}
		params = map[string]interface{}{
			"instrument_name": instrument,
			"side":            "BUY",
			"type":            "MARKET",
			"notional":        fmt.Sprintf("%.4f", notional),
		}
		log.Printf("[Trade Engine] BUY %s | USD Balance: $%.4f | Using %.1f%% = $%.4f\n",
			pair, usdBalance, allocationPct, notional)
	} else {
		baseCurrency := strings.SplitN(pair, "/", 2)[0]
		coinBalance, err := c.GetBalance(baseCurrency)
		if err != nil {
			return "", 0, fmt.Errorf("get %s balance: %w", baseCurrency, err)
		}
		quantity := coinBalance * allocationPct / 100.0
		if quantity <= 0 {
			return "", 0, fmt.Errorf("no %s balance to sell (balance: %f)", baseCurrency, coinBalance)
		}
		notional = quantity
		params = map[string]interface{}{
			"instrument_name": instrument,
			"side":            "SELL",
			"type":            "MARKET",
			"quantity":        fmt.Sprintf("%.8f", quantity),
		}
		log.Printf("[Trade Engine] SELL %s | %s Balance: %.8f | Using %.1f%% = %.8f\n",
			pair, baseCurrency, coinBalance, allocationPct, quantity)
	}

	result, err := c.doRequest("private/create-order", params)
	if err != nil {
		return "", notional, err
	}

	res, ok := result["result"].(map[string]interface{})
	if !ok {
		return "", notional, fmt.Errorf("missing result in order response")
	}

	orderID, ok := res["order_id"].(string)
	if !ok {
		if idFloat, ok := res["order_id"].(float64); ok {
			orderID = fmt.Sprintf("%.0f", idFloat)
		} else {
			return "", notional, fmt.Errorf("order_id not found in response")
		}
	}

	return orderID, notional, nil
}

// StartTradeEngine processes trade intents and executes live orders on Crypto.com.
func StartTradeEngine(ctx context.Context, wg *sync.WaitGroup, qm *queue.Manager) {
	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Println("[Trade Engine] Daemon initialized.")

		exchange := &CryptoComClient{
			APIKey:    os.Getenv("CRYPTO_COM_API_KEY"),
			APISecret: os.Getenv("CRYPTO_COM_SECRET_KEY"),
		}

		if exchange.APIKey != "" {
			log.Println("[Trade Engine] Credentials present; LIVE DISPATCH HELD pending reconciliation")
		} else {
			log.Println("[Trade Engine] No credentials; dispatch disabled (no implicit paper mode)")
		}

		minConfidence := 0.85

		for {
			select {
			case <-ctx.Done():
				log.Println("[Trade Engine] Shutting down...")
				return
			case payload := <-qm.TradeQueue:
				intent, ok := payload["intent"].(map[string]interface{})
				if !ok {
					continue
				}

				confidence, _ := intent["confidence"].(float64)
				if confidence <= minConfidence {
					log.Printf("[Trade Engine] Rejected: confidence %.3f below threshold %.2f\n", confidence, minConfidence)
					continue
				}

				pair, _ := intent["pair"].(string)
				action, _ := intent["action"].(string)
				price, _ := intent["price"].(float64)
				tp, _ := intent["take_profit"].(float64)
				sl, _ := intent["stop_loss"].(float64)
				allocationPct, _ := intent["percentage"].(float64)
				if allocationPct <= 0 {
					allocationPct = getEnvFloat("TRADE_ALLOCATION_PCT", 0.25) * 100.0
				}

				log.Printf("[Trade Engine] Processing %s %s | Confidence: %.3f | Alloc: %.1f%%\n",
					action, pair, confidence, allocationPct)

				txID, notional, err := exchange.CreateOrder(pair, action, allocationPct)
				if err != nil {
					log.Println("[Trade Engine] Order blocked/unknown; no synthetic fill and no automatic retry")
					continue
				}

				log.Printf("[Trade Engine] Order executed! TX_ID: %s\n", txID)

				trackPayload := map[string]interface{}{
					"tx_id":       txID,
					"status":      "completed",
					"pair":        pair,
					"action":      action,
					"amount":      notional,
					"stop_loss":   sl,
					"take_profit": tp,
					"price":       price,
				}
				qm.PushTracking(trackPayload)

				sendDiscordWebhook(txID, pair, action, notional, price, tp, sl)
			}
		}
	}()
}

// No environment switch may bypass unreconciled legacy fill accounting.
func cryptoLiveDispatchBlocked() bool { return true }
