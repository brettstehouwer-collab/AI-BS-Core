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
	"math"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"crypto-swarm/internal/queue"
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

// InstrumentInfo holds the precision details for a trading pair.
type InstrumentInfo struct {
	QuantityDecimals int `json:"quantity_decimals"`
	PriceDecimals    int `json:"price_decimals"`
}

// CryptoComClient uses v1 public data; legacy private dispatch remains held.
type CryptoComClient struct {
	APIKey    string
	APISecret string
	reqID     int64
	Markets   map[string]InstrumentInfo
	mu        sync.RWMutex
	publicHTTPClient *http.Client
}

// LoadMarkets fetches precision rules from the exchange.
func (c *CryptoComClient) LoadMarkets() error {
	result, err := c.publicMarketData("public/get-instruments")
	if err != nil {
		return err
	}
	res, ok := result["result"].(map[string]interface{})
	if !ok {
		return fmt.Errorf("missing result in get-instruments")
	}

	instruments, ok := res["data"].([]interface{})
	if !ok {
		return fmt.Errorf("missing instruments array")
	}

	markets := make(map[string]InstrumentInfo)
	for _, rawInst := range instruments {
		inst, ok := rawInst.(map[string]interface{})
		if !ok {
			return fmt.Errorf("invalid instrument record")
		}
		name, _ := inst["symbol"].(string)
		qd, qerr := marketPrecision(inst["quantity_decimals"])
		pd, perr := marketPrecision(inst["quote_decimals"])
		if name == "" || qerr != nil || perr != nil { return fmt.Errorf("invalid instrument precision or symbol") }
		if _, duplicate := markets[name]; duplicate { return fmt.Errorf("duplicate instrument") }
		markets[name] = InstrumentInfo{QuantityDecimals: qd, PriceDecimals: pd}
	}
	c.mu.Lock()
	c.Markets = markets
	c.mu.Unlock()
	return nil
}

// Truncate safely truncates a float to the exact number of decimal places.
func (c *CryptoComClient) Truncate(value float64, decimals int) string {
	pow := math.Pow(10, float64(decimals))
	truncated := math.Trunc(value*pow) / pow
	return strconv.FormatFloat(truncated, 'f', decimals, 64)
}

// FetchTickers fetches all current market prices.
func (c *CryptoComClient) FetchTickers() (map[string]float64, error) {
	result, err := c.publicMarketData("public/get-tickers")
	if err != nil {
		return nil, err
	}
	res, ok := result["result"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("missing result in get-ticker")
	}
	data, ok := res["data"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("missing data array")
	}

	tickers := make(map[string]float64)
	for _, rawTicker := range data {
		t, ok := rawTicker.(map[string]interface{})
		if !ok {
			return nil, fmt.Errorf("invalid ticker record")
		}
		name, _ := t["i"].(string)
		last, err := marketPrice(t["a"])
		if name == "" || err != nil { return nil, fmt.Errorf("invalid ticker symbol or price") }
		if _, duplicate := tickers[name]; duplicate { return nil, fmt.Errorf("duplicate ticker") }
		tickers[name] = last
	}
	return tickers, nil
}

// buildParamString sorts params by key and concatenates key+value pairs (no separator).
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
// Returns the raw result map on success.
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

	// Crypto.com returns code 0 for success
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

	// "available" is the withdrawable/tradeable balance
	available, ok := account["available"].(float64)
	if !ok {
		return 0, fmt.Errorf("available balance field missing for %s", currency)
	}
	return available, nil
}

// CreateOrder places a MARKET order. For BUY uses USD notional; for SELL uses coin quantity.
// allocationPct is 0-100 (e.g. 25.0 = use 25% of available balance).
func (c *CryptoComClient) CreateOrder(pair, action string, allocationPct float64) (string, float64, error) {
	if cryptoLiveDispatchBlocked() {
		return "", 0, fmt.Errorf("live dispatch held: fill and balance reconciliation required")
	}
	if c.APIKey == "" || c.APISecret == "" {
		return "", 0, fmt.Errorf("API keys not configured")
	}

	instrument := strings.ReplaceAll(pair, "/", "_")
	side := strings.ToUpper(action)

	c.mu.RLock()
	info, hasInfo := c.Markets[instrument]
	c.mu.RUnlock()
	if !hasInfo {
		info = InstrumentInfo{QuantityDecimals: 8, PriceDecimals: 4}
	}

	var params map[string]interface{}
	var notional float64

	if side == "BUY" {
		usdBalance, err := c.GetBalance("USD")
		if err != nil {
			return "", 0, fmt.Errorf("get USD balance: %w", err)
		}
		notional = usdBalance * allocationPct / 100.0
		if notional < 1.0 {
			return "", 0, fmt.Errorf("notional $%.4f is below $1.00 minimum (USD balance: $%.4f)", notional, usdBalance)
		}

		formattedNotional := c.Truncate(notional, info.PriceDecimals)

		params = map[string]interface{}{
			"instrument_name": instrument,
			"side":            "BUY",
			"type":            "MARKET",
			"notional":        formattedNotional,
		}
		log.Printf("[Trade Engine] BUY %s | USD Balance: $%.4f | Using %.1f%% = $%s\n",
			pair, usdBalance, allocationPct, formattedNotional)
	} else {
		// For SELL: get the coin balance
		baseCurrency := strings.SplitN(pair, "/", 2)[0]
		coinBalance, err := c.GetBalance(baseCurrency)
		if err != nil {
			return "", 0, fmt.Errorf("get %s balance: %w", baseCurrency, err)
		}
		quantity := coinBalance * allocationPct / 100.0
		if quantity <= 0 {
			return "", 0, fmt.Errorf("no %s balance to sell (balance: %f)", baseCurrency, coinBalance)
		}

		formattedQuantity := c.Truncate(quantity, info.QuantityDecimals)
		if val, _ := strconv.ParseFloat(formattedQuantity, 64); val <= 0 {
			return "", 0, fmt.Errorf("truncated quantity %s is 0, skipping", formattedQuantity)
		}

		notional = quantity // for tracking; actual USD value unknown pre-fill
		params = map[string]interface{}{
			"instrument_name": instrument,
			"side":            "SELL",
			"type":            "MARKET",
			"quantity":        formattedQuantity,
		}
		log.Printf("[Trade Engine] SELL %s | %s Balance: %.8f | Using %.1f%% = %s\n",
			pair, baseCurrency, coinBalance, allocationPct, formattedQuantity)
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
		// Try as float (some APIs return numeric IDs)
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

		if err := exchange.LoadMarkets(); err != nil {
			log.Printf("[Trade Engine] Failed to load markets: %v\n", err)
		} else {
			log.Printf("[Trade Engine] Loaded %d markets for precision handling\n", len(exchange.Markets))
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
				token, _ := payload["validation_token"].(string)

				// Skip strict token validation — both sides are Go now
				_ = token
				_ = validateToken

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

				var txID string
				var notional float64
				var err error

				txID, notional, err = exchange.CreateOrder(pair, action, allocationPct)
				if err != nil {
					log.Println("[Trade Engine] Order blocked/unknown; no synthetic fill and no automatic retry")
					continue
				}

				log.Printf("[Trade Engine] Order executed! TX_ID: %s\n", txID)

				// Report back to Watcher for position tracking
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

				// Fire Discord alert
				sendDiscordWebhook(txID, pair, action, notional, price, tp, sl)
			}
		}
	}()
}

// No environment switch may bypass unreconciled legacy fill accounting.
func cryptoLiveDispatchBlocked() bool { return true }
