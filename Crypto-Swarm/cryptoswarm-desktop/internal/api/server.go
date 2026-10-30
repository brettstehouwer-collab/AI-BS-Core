package api

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"sync"
	"time"

	"cryptoswarm-desktop/internal/aeo"
	"cryptoswarm-desktop/internal/queue"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
)

// readJSONSafe reads a JSON file into a map.
func readJSONSafe(filePath string) map[string]interface{} {
	data := make(map[string]interface{})
	fileData, err := os.ReadFile(filePath)
	if err != nil {
		return data
	}
	_ = json.Unmarshal(fileData, &data)
	return data
}

// StartServer starts the Fiber API server as a goroutine.
func StartServer(ctx context.Context, wg *sync.WaitGroup, qm *queue.Manager) {
	wg.Add(1)
	go func() {
		defer wg.Done()

		app := fiber.New(fiber.Config{
			DisableStartupMessage: true,
		})

		// Add CORS middleware
		app.Use(cors.New(cors.Config{
			AllowOrigins: "*",
			AllowMethods: "GET,POST,HEAD,PUT,DELETE,PATCH,OPTIONS",
		}))

		app.Get("/api/status", func(c *fiber.Ctx) error {
			// In Go, daemons are running as goroutines so they are always "active"
			// unless they crash. We can implement a registry later if needed.
			return c.JSON(fiber.Map{
				"wallet_tracker": fiber.Map{"running": true},
				"trade_engine":   fiber.Map{"running": true},
				"researcher":     fiber.Map{"running": true},
				"watcher":        fiber.Map{"running": true},
				"drip_trader":    fiber.Map{"running": true},
				"chia_plotter":   fiber.Map{"running": true},
			})
		})

		app.Get("/api/telemetry", func(c *fiber.Ctx) error {
			walletData := readJSONSafe("wallet_telemetry.json")
			computeData := readJSONSafe("compute_telemetry.json")
			cacheData := readJSONSafe("telemetry_cache.json")

			return c.JSON(fiber.Map{
				"wallet":  walletData,
				"compute": computeData,
				"general": cacheData,
			})
		})

		app.Post("/api/advertising/aeo", func(c *fiber.Ctx) error {
			var req aeo.AeoRequest
			if err := c.BodyParser(&req); err != nil {
				return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid JSON"})
			}

			// Fetch live LLM report
			report := aeo.GenerateLiveReport(req)
			return c.JSON(report)
		})

		go func() {
			if err := app.Listen("127.0.0.1:8001"); err != nil {
				log.Printf("[API Server] Failed to start: %v\n", err)
			}
		}()
		log.Println("[API Server] Started on http://127.0.0.1:8001")

		// Wait for context cancellation
		<-ctx.Done()
		log.Println("[API Server] Shutting down...")
		_ = app.ShutdownWithTimeout(5 * time.Second)
	}()
}
