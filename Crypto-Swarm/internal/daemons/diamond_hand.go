package daemons

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"strings"
	"sync"
	"time"

	"crypto-swarm/internal/queue"
)

const ledgerFile = "crypto_ledger.json"

type Position struct {
	Amount       float64 `json:"amount"`
	AvgBuyPrice  float64 `json:"avg_buy_price"`
	LastBuyPrice float64 `json:"last_buy_price"`
}

type Ledger struct {
	Positions       map[string]Position `json:"positions"`
	ReferencePrices map[string]float64  `json:"reference_prices"`
	TotalProfitUSD  float64             `json:"total_profit_usd"`
}

func loadLedger() Ledger {
	data, err := os.ReadFile(ledgerFile)
	if err != nil {
		return Ledger{
			Positions:       make(map[string]Position),
			ReferencePrices: make(map[string]float64),
			TotalProfitUSD:  0.0,
		}
	}
	var l Ledger
	if err := json.Unmarshal(data, &l); err != nil {
		return Ledger{
			Positions:       make(map[string]Position),
			ReferencePrices: make(map[string]float64),
			TotalProfitUSD:  0.0,
		}
	}
	if l.Positions == nil {
		l.Positions = make(map[string]Position)
	}
	if l.ReferencePrices == nil {
		l.ReferencePrices = make(map[string]float64)
	}
	return l
}

func saveLedger(l Ledger) {
	data, _ := json.MarshalIndent(l, "", "    ")
	os.WriteFile(ledgerFile, data, 0644)
}

// StartDiamondHand runs the volatility farming strategy.
func StartDiamondHand(ctx context.Context, wg *sync.WaitGroup, qm *queue.Manager) {
	if cryptoLiveDispatchBlocked() {
		log.Println("[Diamond Hand] Held pending reconciliation; existing ledger preserved")
		return
	}
	wg.Add(1)
	go func() {
		defer wg.Done()
		log.Println("[Diamond Hand] Daemon initialized.")
		log.Println("[Diamond Hand] Strategy: Buy Low, Sell High (Continual Volatility Farming)")

		exchange := &CryptoComClient{
			APIKey:    os.Getenv("CRYPTO_COM_API_KEY"),
			APISecret: os.Getenv("CRYPTO_COM_SECRET_KEY"),
		}

		if err := exchange.LoadMarkets(); err != nil {
			log.Printf("[Diamond Hand] Failed to load markets: %v\n", err)
		}

		symbolsStr := os.Getenv("WATCHER_SYMBOLS")
		if symbolsStr == "" {
			symbolsStr = "BTC/USD,ETH/USD,SOL/USD,DOGE/USD"
		}
		var watcherSymbols []string
		for _, s := range strings.Split(symbolsStr, ",") {
			watcherSymbols = append(watcherSymbols, strings.TrimSpace(s))
		}

		buyDipPct := getEnvFloat("BUY_DIP_PCT", 0.015)
		takeProfitPct := getEnvFloat("TAKE_PROFIT_PCT", 0.02)
		tradeUSDAmount := 2.00 // hardcoded requirement

		ticker := time.NewTicker(15 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				log.Println("[Diamond Hand] Shutting down...")
				return
			case <-ticker.C:
				if exchange.APIKey == "" {
					log.Println("[Diamond Hand] Exchange not connected. Waiting for valid API keys in .env...")
					continue
				}

				ledger := loadLedger()

				usdBalance, err := exchange.GetBalance("USD")
				if err != nil {
					log.Printf("[Diamond Hand] Error fetching USD balance: %v\n", err)
					continue
				}

				tickers, err := exchange.FetchTickers()
				if err != nil {
					log.Printf("[Diamond Hand] Error fetching tickers: %v\n", err)
					continue
				}

				for _, symbol := range watcherSymbols {
					instName := strings.ReplaceAll(symbol, "/", "_")
					price, ok := tickers[instName]
					if !ok || price <= 0 {
						continue
					}

					position, hasPosition := ledger.Positions[symbol]
					refPrice, hasRef := ledger.ReferencePrices[symbol]
					if !hasRef {
						ledger.ReferencePrices[symbol] = price
						saveLedger(ledger)
						log.Printf("[Diamond Hand] [%s] Initialized reference price at $%.4f\n", symbol, price)
						continue
					}

					if hasPosition {
						avgBuyPrice := position.AvgBuyPrice
						profitPct := (price - avgBuyPrice) / avgBuyPrice

						// 1. SWAP LOGIC (Coin-to-Coin Arbitrage)
						if profitPct >= 0.01 {
							var worstSymbol string
							worstDrop := 0.0
							for _, otherSym := range watcherSymbols {
								if otherSym == symbol {
									continue
								}
								otherInst := strings.ReplaceAll(otherSym, "/", "_")
								otherPrice, okP := tickers[otherInst]
								otherRef, okR := ledger.ReferencePrices[otherSym]
								if okP && okR && otherPrice > 0 && otherRef > 0 {
									drop := (otherRef - otherPrice) / otherRef
									if drop > worstDrop {
										worstDrop = drop
										worstSymbol = otherSym
									}
								}
							}

							if worstSymbol != "" && worstDrop >= buyDipPct*2 {
								log.Printf("[Diamond Hand] 🔄 SWAP OPPORTUNITY: %s is up %.2f%%, while %s is down %.2f%%!\n", symbol, profitPct*100, worstSymbol, worstDrop*100)

								txID, _, err := exchange.CreateOrder(symbol, "SELL", 100.0)
								if err != nil {
									log.Printf("[Diamond Hand] Swap step 1 failed (%s): %v\n", symbol, err)
									continue
								}

								time.Sleep(1 * time.Second)

								// For swap buy, we just use 100% allocation of current USD balance (replicating Python script behavior exactly)
								_, notional, err2 := exchange.CreateOrder(worstSymbol, "BUY", 100.0)
								if err2 != nil {
									log.Printf("[Diamond Hand] Swap step 2 failed (%s): %v\n", worstSymbol, err2)
									continue
								}

								log.Printf("[Diamond Hand] -> Swapped %s into %s (TX: %s)\n", symbol, worstSymbol, txID)

								targetPrice := tickers[strings.ReplaceAll(worstSymbol, "/", "_")]
								safeBuyAmt := notional / targetPrice // Approximation

								profit := (price - avgBuyPrice) * position.Amount
								ledger.TotalProfitUSD += profit
								delete(ledger.Positions, symbol)

								if oldPos, exists := ledger.Positions[worstSymbol]; exists {
									oldVal := oldPos.Amount * oldPos.AvgBuyPrice
									newVal := safeBuyAmt * targetPrice
									newAmt := oldPos.Amount + safeBuyAmt
									ledger.Positions[worstSymbol] = Position{
										Amount:       newAmt,
										AvgBuyPrice:  (oldVal + newVal) / newAmt,
										LastBuyPrice: targetPrice,
									}
								} else {
									ledger.Positions[worstSymbol] = Position{
										Amount:       safeBuyAmt,
										AvgBuyPrice:  targetPrice,
										LastBuyPrice: targetPrice,
									}
								}
								ledger.ReferencePrices[symbol] = price
								saveLedger(ledger)
								continue
							}
						}

						// 2. Take Profit (Sell High)
						if profitPct >= takeProfitPct {
							log.Printf("[Diamond Hand] [%s] 💰 In Profit %.2f%%. SELLING HIGH!\n", symbol, profitPct*100)
							_, _, err := exchange.CreateOrder(symbol, "SELL", 100.0)
							if err != nil {
								log.Printf("[Diamond Hand] Failed to sell %s: %v\n", symbol, err)
								continue
							}

							profit := (price - avgBuyPrice) * position.Amount
							ledger.TotalProfitUSD += profit
							delete(ledger.Positions, symbol)
							ledger.ReferencePrices[symbol] = price
							saveLedger(ledger)
							continue
						}

						// 3. DCA / Buy More Dip
						if price < position.LastBuyPrice*(1-buyDipPct) {
							if usdBalance >= tradeUSDAmount {
								log.Printf("[Diamond Hand] [%s] 📉 Dropped %.2f%% below last buy. BUYING MORE DIP!\n", symbol, buyDipPct*100)
								alloc := (tradeUSDAmount / usdBalance) * 100.0
								_, notional, err := exchange.CreateOrder(symbol, "BUY", alloc)
								if err != nil {
									log.Printf("[Diamond Hand] Failed to buy dip %s: %v\n", symbol, err)
									continue
								}
								coinAmt := notional / price

								oldVal := position.Amount * avgBuyPrice
								newVal := coinAmt * price
								newAmt := position.Amount + coinAmt
								ledger.Positions[symbol] = Position{
									Amount:       newAmt,
									AvgBuyPrice:  (oldVal + newVal) / newAmt,
									LastBuyPrice: price,
								}
								usdBalance -= notional
								saveLedger(ledger)
							} else {
								log.Printf("[Diamond Hand] Not enough USD to buy dip for %s.\n", symbol)
							}
						}

					} else {
						// 4. Initial Buy
						if price < refPrice*(1-buyDipPct) {
							if usdBalance >= tradeUSDAmount {
								log.Printf("[Diamond Hand] [%s] 💎 Dropped %.2f%% from reference. BUYING LOW!\n", symbol, buyDipPct*100)
								alloc := (tradeUSDAmount / usdBalance) * 100.0
								_, notional, err := exchange.CreateOrder(symbol, "BUY", alloc)
								if err != nil {
									log.Printf("[Diamond Hand] Failed to buy initial %s: %v\n", symbol, err)
									continue
								}
								coinAmt := notional / price
								ledger.Positions[symbol] = Position{
									Amount:       coinAmt,
									AvgBuyPrice:  price,
									LastBuyPrice: price,
								}
								usdBalance -= notional
								saveLedger(ledger)
							} else {
								log.Printf("[Diamond Hand] Not enough USD to buy initial dip for %s.\n", symbol)
							}
						} else {
							// Trailing stop up/down
							if price > refPrice {
								ledger.ReferencePrices[symbol] = price
								saveLedger(ledger)
							}
						}
					}
				}
			}
		}
	}()
}
