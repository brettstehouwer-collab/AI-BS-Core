package daemons

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"strconv"
	"sync"

	"crypto-swarm/internal/queue"
)

func generateToken(intent map[string]interface{}) string {
	intentBytes, _ := json.Marshal(intent)
	hash := sha256.Sum256([]byte(fmt.Sprintf("%s:%s", intentBytes, "matrix_execution_secret_77")))
	return hex.EncodeToString(hash[:])
}

func getEnvFloat(key string, def float64) float64 {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	f, err := strconv.ParseFloat(v, 64)
	if err != nil {
		return def
	}
	return f
}

// StartResearcher translates researcher.py
func StartResearcher(ctx context.Context, wg *sync.WaitGroup, qm *queue.Manager) {
	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Println("[Researcher] Daemon initialized.")

		for {
			select {
			case <-ctx.Done():
				log.Println("[Researcher] Shutting down...")
				return
			case payload := <-qm.ResearchQueue:
				log.Printf("[Researcher] Received trigger from Watcher: %v\n", payload)

				currentPrice, _ := payload["current_price"].(float64)
				drawdownPct, ok := payload["drawdown_pct"].(float64)
				if !ok {
					drawdownPct = 3.0
				}
				eventType, ok := payload["event"].(string)
				if !ok {
					eventType = "price_drop_3pct"
				}

				if currentPrice > 0 {
					tpPct := getEnvFloat("TAKE_PROFIT_PCT", 0.10)
					slPct := getEnvFloat("STOP_LOSS_PCT", 0.05)

					stopLossPrice := currentPrice * (1.0 - slPct)
					takeProfitPrice := currentPrice * (1.0 + tpPct)

					action := "BUY"
					confidenceScore := 0.99

					if eventType == "price_drop_3pct" {
						baseConfidence := 0.85
						bonus := math.Max(0, drawdownPct-3.0) / 7.0 * 0.14
						bonus = math.Min(0.14, bonus)
						confidenceScore = math.Round((baseConfidence+bonus)*1000) / 1000
						action = "BUY"
					} else if eventType == "rsi_oversold" {
						// RSI < 30: scale confidence from 0.85 (RSI=30) to 0.99 (RSI=10)
						rsi, hasRSI := payload["rsi"].(float64)
						if hasRSI {
							rsiBonus := math.Max(0, 30.0-rsi) / 20.0 * 0.14
							confidenceScore = math.Min(0.99, math.Round((0.85+rsiBonus)*1000)/1000)
						} else {
							confidenceScore = 0.88
						}
						action = "BUY"
						log.Printf("[Researcher] RSI BUY signal for %s — confidence %.3f\n", payload["pair"], confidenceScore)
					} else if eventType == "take_profit_hit" || eventType == "stop_loss_hit" || eventType == "rsi_overbought" {
						action = "SELL"
						confidenceScore = 0.99
						log.Printf("[Researcher] Processing SELL event: %s\n", eventType)
					}

					allocPct := 100.0
					if action == "BUY" {
						allocPct = getEnvFloat("TRADE_ALLOCATION_PCT", 0.25) * 100.0
					}

					pair, _ := payload["pair"].(string)

					baseIntent := map[string]interface{}{
						"action":      action,
						"target":      "market",
						"pair":        pair,
						"amount_type": "percentage",
						"percentage":  allocPct,
						"price":       currentPrice,
						"stop_loss":   0.0,
						"take_profit": 0.0,
						"confidence":  confidenceScore,
					}
					if action == "BUY" {
						baseIntent["stop_loss"] = stopLossPrice
						baseIntent["take_profit"] = takeProfitPrice
					}

					validationToken := generateToken(baseIntent)

					tradeIntent := map[string]interface{}{
						"intent":           baseIntent,
						"validation_token": validationToken,
					}

					log.Printf("[Researcher] Generated trade intent for %.2f%% allocation of %s with confidence %.3f\n", allocPct, pair, confidenceScore)
					qm.PushTrade(tradeIntent)
				}
			}
		}
	}()
}
