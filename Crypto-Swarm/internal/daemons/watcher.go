package daemons

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"crypto-swarm/internal/queue"
)

const stateFile = "active_positions.json"

func loadActivePositions() map[string]map[string]interface{} {
	data := make(map[string]map[string]interface{})
	fileData, err := os.ReadFile(stateFile)
	if err == nil {
		_ = json.Unmarshal(fileData, &data)
	}
	return data
}

func saveActivePositions(positions map[string]map[string]interface{}) {
	fileData, err := json.MarshalIndent(positions, "", "  ")
	if err == nil {
		_ = os.WriteFile(stateFile, fileData, 0644)
	}
}

func fetchTickerPrice(symbol string) float64 {
	// crypto.com uses formatting like ETH_USD instead of ETH/USD
	instrument := strings.ReplaceAll(symbol, "/", "_")
	url := fmt.Sprintf("https://api.crypto.com/v2/public/get-ticker?instrument_name=%s", instrument)

	resp, err := http.Get(url)
	if err != nil {
		return 0.0
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0.0
	}

	var data map[string]interface{}
	if err := json.Unmarshal(body, &data); err != nil {
		return 0.0
	}

	result, ok := data["result"].(map[string]interface{})
	if !ok {
		return 0.0
	}

	dataNode, ok := result["data"].([]interface{})
	if !ok || len(dataNode) == 0 {
		return 0.0
	}

	tickerNode, ok := dataNode[0].(map[string]interface{})
	if !ok {
		return 0.0
	}

	price, _ := tickerNode["a"].(float64) // "a" is typically the last trade price or ask in their API, "a" is best ask, "b" is best bid. Let's use "a"
	return price
}

func StartWatcher(ctx context.Context, wg *sync.WaitGroup, qm *queue.Manager) {
	if cryptoLiveDispatchBlocked() {
		log.Println("[Watcher] Held pending fill reconciliation; existing positions preserved")
		return
	}

	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Println("[Watcher] Daemon initialized.")

		symbolsEnv := os.Getenv("WATCHER_SYMBOLS")
		if symbolsEnv == "" {
			symbolsEnv = "ETH/USD,SOL/USD,XRP/USD,ADA/USD,DOGE/USD,AVAX/USD,LINK/USD"
		}

		var symbols []string
		for _, s := range strings.Split(symbolsEnv, ",") {
			s = strings.TrimSpace(s)
			if s != "" {
				symbols = append(symbols, s)
			}
		}

		pollIntervalStr := os.Getenv("WATCHER_POLL_INTERVAL")
		pollInterval := 15
		if pollIntervalStr != "" {
			fmt.Sscanf(pollIntervalStr, "%d", &pollInterval)
		}

		dropThreshold := getEnvFloat("WATCHER_DROP_THRESHOLD", 0.03)

		rollingHighs := make(map[string]float64)
		for _, sym := range symbols {
			rollingHighs[sym] = 0.0
		}

		activePositions := loadActivePositions()
		log.Printf("[Watcher] Scanning %d assets: %v\n", len(symbols), symbols)
		log.Printf("[Watcher] Loaded %d active positions.\n", len(activePositions))

		ticker := time.NewTicker(time.Duration(pollInterval) * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				log.Println("[Watcher] Shutting down...")
				return
			case trackEvent := <-qm.WatcherTrackingQueue:
				log.Printf("[Watcher] Received trade execution report: %v\n", trackEvent)
				action, _ := trackEvent["action"].(string)
				pair, _ := trackEvent["pair"].(string)

				if action == "BUY" || action == "buy" {
					if oldPos, exists := activePositions[pair]; exists {
						oldAmount, _ := oldPos["amount"].(float64)
						oldPrice, _ := oldPos["buy_price"].(float64)
						newAmount, _ := trackEvent["amount"].(float64)
						newPrice, _ := trackEvent["price"].(float64)

						totalAmount := oldAmount + newAmount
						var avgPrice float64
						if totalAmount > 0 {
							avgPrice = (oldAmount*oldPrice + newAmount*newPrice) / totalAmount
						} else {
							avgPrice = newPrice
						}

						tpPct := getEnvFloat("TAKE_PROFIT_PCT", 0.10)
						slPct := getEnvFloat("STOP_LOSS_PCT", 0.05)

						activePositions[pair] = map[string]interface{}{
							"buy_price":   avgPrice,
							"stop_loss":   avgPrice * (1.0 - slPct),
							"take_profit": avgPrice * (1.0 + tpPct),
							"amount":      totalAmount,
						}
						log.Printf("[Watcher] DCA Position averaged down for %s. New Avg: %.4f\n", pair, avgPrice)
					} else {
						activePositions[pair] = map[string]interface{}{
							"buy_price":   trackEvent["price"],
							"stop_loss":   trackEvent["stop_loss"],
							"take_profit": trackEvent["take_profit"],
							"amount":      trackEvent["amount"],
						}
						log.Printf("[Watcher] Position saved for %s\n", pair)
					}
					saveActivePositions(activePositions)
				} else if action == "SELL" || action == "sell" {
					delete(activePositions, pair)
					saveActivePositions(activePositions)
					log.Printf("[Watcher] Position closed for %s\n", pair)
				}
			case <-ticker.C:
				for _, sym := range symbols {
					currentPrice := fetchTickerPrice(sym)
					if currentPrice <= 0 {
						continue
					}

					if currentPrice > rollingHighs[sym] {
						rollingHighs[sym] = currentPrice
					}

					high := rollingHighs[sym]
					if high > 0 {
						drawdown := (high - currentPrice) / high
						if drawdown >= dropThreshold {
							log.Printf("[Watcher] Anomaly! %s dropped by %.2f%% from $%.4f\n", sym, drawdown*100, high)

							payload := map[string]interface{}{
								"pair":          sym,
								"event":         "price_drop_3pct",
								"timestamp":     time.Now().UTC().Format(time.RFC3339),
								"current_price": currentPrice,
								"drawdown_pct":  math.Round(drawdown*10000) / 100,
							}
							qm.PushResearch(payload)

							rollingHighs[sym] = currentPrice
						}
					}

					if pos, exists := activePositions[sym]; exists {
						sl, _ := pos["stop_loss"].(float64)
						tp, _ := pos["take_profit"].(float64)

						if sl > 0 && currentPrice <= sl {
							log.Printf("[Watcher] Stop-Loss hit for %s! Triggering sell.\n", sym)
							payload := map[string]interface{}{
								"pair":          sym,
								"event":         "stop_loss_hit",
								"timestamp":     time.Now().UTC().Format(time.RFC3339),
								"current_price": currentPrice,
							}
							qm.PushResearch(payload)
							delete(activePositions, sym)
							saveActivePositions(activePositions)
						} else if tp > 0 && currentPrice >= tp {
							log.Printf("[Watcher] Take-Profit hit for %s! Triggering sell.\n", sym)
							payload := map[string]interface{}{
								"pair":          sym,
								"event":         "take_profit_hit",
								"timestamp":     time.Now().UTC().Format(time.RFC3339),
								"current_price": currentPrice,
							}
							qm.PushResearch(payload)
							delete(activePositions, sym)
							saveActivePositions(activePositions)
						}
					}
				}
			}
		}
	}()
}
